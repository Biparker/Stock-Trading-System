"""
Earnings & Event Calendar Guard
================================
Post-Stage 5 guard that checks all held, planned-to-buy, and monitored tickers
for upcoming earnings announcements and ex-dividend dates within a configurable
look-ahead window (default: EVENT_GUARD_WINDOW_DAYS env var, fallback 10 days).

Data source: yfinance (already installed, no API key required).
Cache: data/earnings_cache.json — avoids redundant API calls within a pipeline run.
"""

import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional

import yfinance as yf
from dotenv import load_dotenv

from mellea_schemas import DailyAction, EventAlert

load_dotenv()

logger = logging.getLogger("mellea_pipeline")

_CACHE_PATH = Path(__file__).parent / "data" / "earnings_cache.json"


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(cache, indent=2))
    except Exception as exc:
        logger.warning(f"[EventGuard] Could not write cache: {exc}")


def _cache_key(ticker: str) -> str:
    """Cache key expires daily — stale entries from prior days are simply ignored."""
    return f"{ticker}_{date.today().isoformat()}"


def _to_date(value) -> Optional[date]:
    """Convert yfinance's various date representations to a Python date, or None."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        # Unix timestamp
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).date()
        except Exception:
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            return None
    return None


def _fetch_events(ticker: str, cache: dict) -> dict:
    """
    Return {"earnings": date|None, "ex_dividend": date|None} for the ticker.
    Uses today-keyed cache to avoid repeated API calls in one run.
    """
    key = _cache_key(ticker)
    if key in cache:
        raw = cache[key]
        return {
            "earnings": _to_date(raw.get("earnings")),
            "ex_dividend": _to_date(raw.get("ex_dividend")),
        }

    earnings_date: Optional[date] = None
    ex_div_date: Optional[date] = None

    try:
        t = yf.Ticker(ticker)

        # --- Earnings date ---
        cal = t.calendar  # dict or None depending on yfinance version
        if isinstance(cal, dict):
            # yfinance >= 0.2.x returns {"Earnings Date": [Timestamp, ...], ...}
            raw_earnings = cal.get("Earnings Date") or cal.get("Earnings High") or cal.get("Earnings Low")
            if isinstance(raw_earnings, list) and raw_earnings:
                # Pick the earliest future date from the list
                candidates = [_to_date(d) for d in raw_earnings]
                future = [d for d in candidates if d and d >= date.today()]
                if future:
                    earnings_date = min(future)
            else:
                earnings_date = _to_date(raw_earnings)

        # --- Ex-dividend date ---
        info = t.info or {}
        ex_div_date = _to_date(info.get("exDividendDate"))

    except Exception as exc:
        logger.warning(f"[EventGuard] yfinance error for {ticker}: {exc}")

    # Store as ISO strings in cache (JSON-serialisable)
    cache[key] = {
        "earnings": earnings_date.isoformat() if earnings_date else None,
        "ex_dividend": ex_div_date.isoformat() if ex_div_date else None,
    }
    return {"earnings": earnings_date, "ex_dividend": ex_div_date}


def _severity(days: int) -> str:
    if days <= 3:
        return "critical"
    if days <= 7:
        return "warning"
    return "info"


def _recommendation(event_type: str, days: int, context: str) -> str:
    event_label = "earnings" if event_type == "earnings" else "ex-dividend date"
    if days <= 3:
        return f"{'Sell or hedge before' if context in ('hold', 'buy') else 'Avoid entering before'} {event_label} in {days} day{'s' if days != 1 else ''}"
    if days <= 7:
        return f"Review position — {event_label} in {days} days; consider reducing size"
    return f"Monitor: {event_label} in {days} days — no immediate action required"


class EarningsCalendarGuard:
    """
    Checks tickers from a DailyAction for upcoming earnings and ex-dividend events.
    Window size is controlled by EVENT_GUARD_WINDOW_DAYS env variable (default 10).
    """

    def __init__(self) -> None:
        self.window_days: int = int(os.environ.get("EVENT_GUARD_WINDOW_DAYS", 10))

    def get_alerts(self, action: DailyAction) -> List[EventAlert]:
        """
        Return EventAlert objects for any tickers in buy/hold/monitor lists
        that have earnings or ex-dividend events within self.window_days.
        Results are sorted by days_until_event ascending.
        """
        context_map: dict[str, str] = {}
        for t in action.tickers_to_buy:
            context_map[t] = "buy"
        for t in action.tickers_to_hold:
            context_map[t] = "hold"
        for t in action.tickers_to_monitor:
            if t not in context_map:
                context_map[t] = "monitor"

        cache = _load_cache()
        alerts: List[EventAlert] = []
        today = date.today()

        for ticker, context in context_map.items():
            events = _fetch_events(ticker, cache)
            for event_type, event_date in [("earnings", events["earnings"]), ("ex_dividend", events["ex_dividend"])]:
                if event_date is None:
                    continue
                days = (event_date - today).days
                if 0 <= days <= self.window_days:
                    sev = _severity(days)
                    alerts.append(EventAlert(
                        ticker=ticker,
                        event_type=event_type,
                        event_date=event_date.isoformat(),
                        days_until_event=days,
                        position_context=context,
                        severity=sev,
                        recommendation=_recommendation(event_type, days, context),
                    ))
                    if sev in ("critical", "warning"):
                        logger.warning(
                            f"[EventGuard] {ticker}: {event_type} in {days} days "
                            f"({sev}) — {context} position"
                        )

        _save_cache(cache)
        return sorted(alerts, key=lambda a: a.days_until_event)
