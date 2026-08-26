"""
Data loader for the Streamlit dashboard.

Reads pipeline_output.json (written by daily_pipeline.py) and
supplements it with raw forecast series from the existing JSON files
in forecasts/ and Analysis_Outcomes/.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# Paths relative to stock-trading-system/
BASE_DIR      = Path(__file__).parent.parent
DATA_DIR      = BASE_DIR / "data"
FORECASTS_DIR = BASE_DIR / "forecasts"
OUTCOMES_DIR  = BASE_DIR / "Analysis_Outcomes"

PIPELINE_OUTPUT = DATA_DIR / "pipeline_output.json"

# ── Default/fallback data used when pipeline hasn't run yet ──────────────────
_DEFAULT_TICKERS = ["AMGN", "JNJ", "MU", "META", "C"]


def load_pipeline_output() -> dict:
    """
    Load the latest pipeline output.
    Falls back to a minimal stub if the file doesn't exist yet,
    so the dashboard renders in offline/first-run mode.
    """
    if PIPELINE_OUTPUT.exists():
        with open(PIPELINE_OUTPUT, encoding="utf-8") as f:
            data = json.load(f)
        # Back-fill missing keys so the UI never KeyErrors
        data.setdefault("all_tickers",       _DEFAULT_TICKERS)
        data.setdefault("tickers_to_buy",    [])
        data.setdefault("tickers_to_sell",   [])
        data.setdefault("tickers_to_hold",   [])
        data.setdefault("tickers_to_monitor",[])
        data.setdefault("stop_loss_orders",  {})
        data.setdefault("combined_scores",   {})
        data.setdefault("cash_remaining",    2500.0)
        data.setdefault("user_prompt",
                        "Pipeline has not run yet. "
                        "Run `python daily_pipeline.py --mock` to generate data.")
        data.setdefault("forecast",  {})
        data.setdefault("sentiment", {})
        data.setdefault("backtest",  {})
        data.setdefault("actions_by_ticker", {})
        data.setdefault("mode", "unknown")
        return data

    # No pipeline output yet — return stub so dashboard still loads
    return {
        "date":             datetime.now().strftime("%Y-%m-%d"),
        "mode":             "no_data",
        "budget":           2500.0,
        "cash_remaining":   2500.0,
        "all_tickers":      _DEFAULT_TICKERS,
        "tickers_to_buy":   [],
        "tickers_to_sell":  [],
        "tickers_to_hold":  [],
        "tickers_to_monitor": [],
        "stop_loss_orders": {},
        "combined_scores":  {},
        "user_prompt":      "No pipeline data yet. Run `python daily_pipeline.py --mock` first.",
        "forecast":  {},
        "sentiment": {},
        "backtest":  {},
        "actions_by_ticker": {},
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
