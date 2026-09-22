"""
Data loader for the Streamlit dashboard.

Reads pipeline_output.json (written by daily_pipeline.py) and
supplements it with raw forecast series from the existing JSON files
in forecasts/ and Analysis_Outcomes/.

Also merges any single-ticker run files (e.g. jnj_pipeline_output.json)
produced by run_jnj.py, so a targeted re-run automatically refreshes
that ticker's data without a full pipeline re-run.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Paths relative to stock-trading-system/
BASE_DIR      = Path(__file__).parent.parent
DATA_DIR      = BASE_DIR / "data"
FORECASTS_DIR = BASE_DIR / "forecasts"
OUTCOMES_DIR  = BASE_DIR / "Analysis_Outcomes"

PIPELINE_OUTPUT     = DATA_DIR / "pipeline_output.json"
JNJ_PIPELINE_OUTPUT = DATA_DIR / "jnj_pipeline_output.json"

# ── Default/fallback data used when pipeline hasn't run yet ──────────────────
_DEFAULT_TICKERS = ["AMGN", "JNJ"]


def _merge_single_ticker_output(data: dict, single_path: Path) -> dict:
    """
    Merge a single-ticker pipeline output (e.g. jnj_pipeline_output.json)
    into the multi-ticker data dict, replacing that ticker's entries when
    the single-ticker file is same date or newer than the main pipeline run.

    This means running `python run_jnj.py` automatically updates the
    dashboard for JNJ without needing a full pipeline re-run.
    """
    if not single_path.exists():
        return data
    try:
        with open(single_path, encoding="utf-8") as f:
            single = json.load(f)
        ticker = single.get("ticker")
        if not ticker:
            return data
        # Only merge if the single-ticker run is same date or newer
        if single.get("date", "") < data.get("date", ""):
            return data
        # Merge forecast / sentiment / backtest sections
        for section in ("forecast", "sentiment", "backtest"):
            val = single.get(section)
            if val:
                data.setdefault(section, {})[ticker] = val
        # Merge combined score
        score = single.get("combined_scores", {}).get(ticker)
        if score is not None:
            data.setdefault("combined_scores", {})[ticker] = score
        # Derive action from the single-ticker advisor lists
        action = None
        if ticker in single.get("tickers_to_buy",      []): action = "buy"
        elif ticker in single.get("tickers_to_sell",   []): action = "sell"
        elif ticker in single.get("tickers_to_hold",   []): action = "hold"
        elif ticker in single.get("tickers_to_monitor",[]): action = "monitor"
        if action:
            data.setdefault("actions_by_ticker", {})[ticker] = action
        # Ensure ticker appears in the selector list
        if ticker not in data.get("all_tickers", []):
            data.setdefault("all_tickers", []).append(ticker)
    except Exception:
        pass  # never crash the dashboard on a bad merge file
    return data


def load_pipeline_output() -> dict:
    """
    Load the latest pipeline output.
    Also merges any single-ticker run files so the dashboard stays fresh
    after targeted re-runs (e.g. python run_jnj.py).
    Falls back to a minimal stub if the file doesn't exist yet.
    """
    if PIPELINE_OUTPUT.exists():
        with open(PIPELINE_OUTPUT, encoding="utf-8") as f:
            data = json.load(f)
        # Back-fill missing keys so the UI never KeyErrors
        data.setdefault("all_tickers",        _DEFAULT_TICKERS)
        data.setdefault("tickers_to_buy",     [])
        data.setdefault("tickers_to_sell",    [])
        data.setdefault("tickers_to_hold",    [])
        data.setdefault("tickers_to_monitor", [])
        data.setdefault("stop_loss_orders",   {})
        data.setdefault("combined_scores",    {})
        data.setdefault("cash_remaining",     2500.0)
        data.setdefault("user_prompt",
                        "Pipeline has not run yet. "
                        "Run `python daily_pipeline.py --mock` to generate data.")
        data.setdefault("forecast",           {})
        data.setdefault("sentiment",          {})
        data.setdefault("backtest",           {})
        data.setdefault("actions_by_ticker",  {})
        data.setdefault("mode", "unknown")
        # Overlay any newer single-ticker runs
        data = _merge_single_ticker_output(data, JNJ_PIPELINE_OUTPUT)
        return data

    # No pipeline output yet — return stub so dashboard still loads
    return {
        "date":               datetime.now().strftime("%Y-%m-%d"),
        "mode":               "no_data",
        "budget":             2500.0,
        "cash_remaining":     2500.0,
        "all_tickers":        _DEFAULT_TICKERS,
        "tickers_to_buy":     [],
        "tickers_to_sell":    [],
        "tickers_to_hold":    [],
        "tickers_to_monitor": [],
        "stop_loss_orders":   {},
        "combined_scores":    {},
        "user_prompt":        "No pipeline data yet. Run `python daily_pipeline.py --mock` first.",
        "forecast":           {},
        "sentiment":          {},
        "backtest":           {},
        "actions_by_ticker":  {},
    }


def load_forecast_series(ticker: str) -> list[dict]:
    """
    Load the raw daily forecast_results array for Plotly chart rendering.
    Looks in forecasts/ first, then time_series_analyzer/output/.
    Returns [] if not found.
    """
    paths = [
        FORECASTS_DIR / f"{ticker}_forecast_report.json",
        BASE_DIR / "time_series_analyzer" / "output" / f"{ticker}_forecast_report.json",
    ]
    for p in paths:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("forecast_results", [])
    return []


def load_forecast_metadata(ticker: str) -> dict:
    """
    Load full forecast JSON metadata for a ticker.
    Returns {} if not found.
    """
    paths = [
        FORECASTS_DIR / f"{ticker}_forecast_report.json",
        BASE_DIR / "time_series_analyzer" / "output" / f"{ticker}_forecast_report.json",
    ]
    for p in paths:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


def load_backtest_raw(ticker: str) -> dict:
    """
    Load raw stage2 backtest JSON for a ticker.
    Returns {} if not found.
    """
    path = OUTCOMES_DIR / f"{ticker}_stage2_backtest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def get_action_badge(action: str) -> tuple[str, str]:
    """Return (label, color) for a given portfolio action string."""
    mapping = {
        "buy":     ("BUY",     "green"),
        "sell":    ("SELL",    "red"),
        "hold":    ("HOLD",    "orange"),
        "monitor": ("MONITOR", "blue"),
    }
    return mapping.get(action, ("—", "gray"))

# Made with Bob
