"""
mellea_shim.py — Compatibility shim for mellea_agents.py
=========================================================
The agents were written against a decorator-style API:

    @mellea.function(output_schema=MySchema, rules=[...])
    def my_fn(arg: str) -> MySchema: ...

The installed mellea 0.7.x uses start_session() + session.instruct().
This shim bridges the two so mellea_agents.py and daily_pipeline.py
require zero changes.

Usage (daily_pipeline.py already does this):
    import mellea_shim as mellea          # swap the import
    mellea.configure(backend, model, api_key)

Made with IBM Bob
"""

from __future__ import annotations

import json
import logging
import os
import time
from functools import wraps
from typing import Any, Callable, List, Optional, Type

from pydantic import BaseModel

log = logging.getLogger(__name__)

# ── Global session config (set by configure()) ────────────────────────────────
_backend:  str = "ollama"
_model:    str = "llama3"
_api_key:  Optional[str] = None


def configure(
    backend:  str = "ollama",
    model:    str = "llama3",
    api_key:  Optional[str] = None,
):
    """Configure the LLM backend for all @mellea.function calls."""
    global _backend, _model, _api_key
    _backend = backend
    _model   = model
    _api_key = api_key
    log.info(f"mellea_shim configured: backend={backend}, model={model}")


# ── Core: call the model and parse into a Pydantic schema ─────────────────────

def _call_llm(prompt: str) -> str:
    """Make a single LLM call via raw HTTP — avoids all SDK version conflicts."""
    import requests as _req
    import certifi
    import urllib3

    # Suppress SSL warnings for corporate antivirus fallback
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Configure SSL with fallback for corporate antivirus (Norton) interception
    _verify_ssl = certifi.where()

    if _backend == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        payload = {
            "model":  _model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        resp = _req.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    if _backend == "openai":
        key = _api_key or os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to .env or call mellea.configure(api_key=...)"
            )
        payload = {
            "model":       _model,
            "messages":    [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
        }
        for rate_attempt in range(1, 6):   # up to 5 retries on 429
            try:
                resp = _req.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                    verify=_verify_ssl,
                )
            except _req.exceptions.SSLError:
                # Fallback for corporate antivirus (Norton) interception
                log.warning("SSL verification failed; retrying without verification (corporate firewall detected)")
                resp = _req.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                    verify=False,
                )
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30)) + 5
                log.warning(f"Rate limited (attempt {rate_attempt}/5) — waiting {retry_after}s")
                time.sleep(retry_after)
                continue   # re-POST, don't raise on the old response
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"] or ""
        # exhausted rate-limit retries — raise the last 429
        resp.raise_for_status()

    # Fallback for other backends via mellea start_session
    from mellea import start_session
    key = _api_key or os.environ.get("OPENAI_API_KEY", "")
    if key and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = key
    session = start_session(_backend, _model, model_options={"temperature": 0.2})
    result  = session.instruct(prompt)
    session.cleanup()
    return str(result)


def _extract_json(text: str) -> str:
    """Pull the first JSON object or array out of a text response."""
    # Try to find a ```json ... ``` block first
    import re
    block = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if block:
        return block.group(1)
    # Fall back to the first { ... } in the response
    start = text.find("{")
    if start != -1:
        depth, end = 0, start
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        return text[start : end + 1]
    return text


def _parse_schema(text: str, schema: Type[BaseModel]) -> BaseModel:
    """Parse LLM text into a Pydantic schema, with one retry on failure."""
    raw_json = _extract_json(text)
    try:
        data = json.loads(raw_json)
        # Auto-normalise known 0-1 float fields that the LLM sometimes returns
        # as 0-100 percentages (e.g. confidence: 67.79 instead of 0.68).
        # Dividing by 100 is safe because valid fractional values are always < 2.
        for field in ("confidence", "model_confidence"):
            if field in data and isinstance(data[field], (int, float)) and data[field] > 1.0:
                data[field] = round(data[field] / 100.0, 6)
        return schema(**data)
    except Exception as e:
        raise ValueError(
            f"Could not parse LLM response into {schema.__name__}: {e}\n"
            f"Raw response snippet: {text[:400]}"
        ) from e


def _build_prompt(fn: Callable, kwargs: dict, schema: Type[BaseModel], rules: List[str]) -> str:
    """Build the full prompt from the function docstring + schema + IVR rules."""
    # Interpolate {variable} placeholders in docstring.
    # String values (e.g. JSON blobs) may themselves contain { } which would
    # confuse str.format() — escape their braces first so they pass through
    # literally, then unescape after substitution.
    doc = fn.__doc__ or ""
    safe_kwargs = {
        k: v.replace("{", "{{").replace("}", "}}") if isinstance(v, str) else v
        for k, v in kwargs.items()
    }
    try:
        doc = doc.format(**safe_kwargs)
    except KeyError:
        pass  # leave unmatched placeholders as-is

    schema_json = json.dumps(schema.model_json_schema(), indent=2)

    rules_text = ""
    if rules:
        rules_text = "\n\nBUSINESS RULES (you MUST obey all of these):\n"
        rules_text += "\n".join(f"  - {r}" for r in rules)

    return (
        f"{doc}\n\n"
        f"You MUST respond with a single valid JSON object that conforms exactly "
        f"to this JSON Schema — no prose, no markdown fences, just the JSON:\n\n"
        f"{schema_json}"
        f"{rules_text}"
    )


# ── The decorator ─────────────────────────────────────────────────────────────

def function(
    output_schema: Type[BaseModel],
    rules:    List[str] = (),
    sampling: str = "greedy",   # "greedy" | "majority_vote" | "rejection"
    max_retries: int = 3,
):
    """
    @mellea.function decorator.

    Wraps a function whose docstring is the LLM prompt.
    The decorated function ignores its own body and instead:
      1. Builds a prompt from the docstring (with {variable} interpolation)
      2. Calls the LLM
      3. Parses + validates the response against output_schema
      4. Retries up to max_retries times if validation fails (IVR)
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> BaseModel:
            # Merge positional args into kwargs using the function signature
            import inspect
            sig    = inspect.signature(fn)
            params = list(sig.parameters.keys())
            for i, val in enumerate(args):
                if i < len(params):
                    kwargs[params[i]] = val

            prompt = _build_prompt(fn, kwargs, output_schema, list(rules))

            # majority_vote: run 3 times and return the true majority result.
            # Serialise each result to JSON and compare — whichever serialisation
            # appears most often wins. On a 3-way tie (all different) the result
            # with the highest combined_score sum is preferred.
            if sampling == "majority_vote":
                results = []
                for _ in range(3):
                    try:
                        text   = _call_llm(prompt)
                        result = _parse_schema(text, output_schema)
                        results.append(result)
                    except Exception as e:
                        log.warning(f"majority_vote sample failed: {e}")
                if not results:
                    raise RuntimeError(f"All majority_vote samples failed for {fn.__name__}")
                if len(results) == 1:
                    return results[0]

                # Compare only structural decision fields — exclude free-text fields
                # (user_prompt, date, reasoning) that will always differ between samples
                # and would prevent a genuine majority from being detected.
                _PROSE_FIELDS = {"user_prompt", "date", "reasoning"}
                def _decision_key(r) -> str:
                    d = r.model_dump(exclude_none=True)
                    structural = {k: v for k, v in d.items() if k not in _PROSE_FIELDS}
                    return json.dumps(structural, sort_keys=True, default=str)

                from collections import Counter
                serial = [_decision_key(r) for r in results]
                counts = Counter(serial)
                majority_key, majority_count = counts.most_common(1)[0]
                if majority_count >= 2:
                    # A genuine majority exists — return the matching result
                    for r, s in zip(results, serial):
                        if s == majority_key:
                            log.info(f"{fn.__name__} majority_vote: {majority_count}/3 agree on decisions")
                            return r
                # All three differ structurally — pick the one with the highest combined_scores sum
                def _score_sum(r) -> float:
                    scores = getattr(r, "combined_scores", None)
                    return sum(scores.values()) if isinstance(scores, dict) else 0.0
                best = max(results, key=_score_sum)
                log.info(f"{fn.__name__} majority_vote: no majority — returning highest-score result")
                return best

            # greedy / rejection: call once, retry on validation failure
            last_error: Exception = Exception("No attempts made")
            for attempt in range(1, max_retries + 1):
                try:
                    text   = _call_llm(prompt)
                    result = _parse_schema(text, output_schema)
                    log.info(f"{fn.__name__} succeeded on attempt {attempt}")
                    return result
                except Exception as e:
                    last_error = e
                    log.warning(f"{fn.__name__} attempt {attempt}/{max_retries} failed: {e}")
                    if attempt < max_retries:
                        time.sleep(5 * attempt)  # 5s, 10s backoff between retries
                    # Append the error as a repair hint for the next attempt
                    prompt += (
                        f"\n\nPREVIOUS ATTEMPT FAILED — repair the following error "
                        f"and return corrected JSON:\n{e}"
                    )

            raise RuntimeError(
                f"{fn.__name__} failed after {max_retries} attempts. "
                f"Last error: {last_error}"
            )

        return wrapper
    return decorator

# Made with IBM Bob
