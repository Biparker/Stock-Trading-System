"""
Daily MeLLeA Pipeline — Stock Trading System
=============================================
Runs once each morning (7 AM EST via Railway cron, or manually for local testing).

Stages:
  1  Screen S&P500 candidates → MeLLeA select_candidates()
  2  XGBoost 30-day forecast  → MeLLeA interpret_forecast()
  3  FinBERT sentiment        → MeLLeA interpret_sentiment()
  4  Load backtest JSONs      → MeLLeA interpret_backtest()
  5  Daily advisor            → MeLLeA daily_advisor()

Output: data/pipeline_output.json  — read by the Streamlit dashboard.

Usage (local):
    python daily_pipeline.py                        # full live run
    python daily_pipeline.py --mock                 # offline mock run (no LLM calls)
    python daily_pipeline.py --output custom.json   # custom output path
"""

import argparse
import json
import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# ── Ensure data/ exists before logging tries to write there ──────────────────
_DATA_DIR_EARLY = Path(__file__).parent / "data"
_DATA_DIR_EARLY.mkdir(exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(_DATA_DIR_EARLY / "pipeline.log"), mode="a"),
    ],
)
log = logging.getLogger(__name__)

# ── Paths (all relative to stock-trading-system/) ────────────────────────────
BASE_DIR        = Path(__file__).parent
FORECASTS_DIR   = BASE_DIR / "forecasts"
OUTCOMES_DIR    = BASE_DIR / "Analysis_Outcomes"
ANALYST_DIR     = BASE_DIR / "sentiment_analyzer" / "Analyst_reports"
SENT_OUTPUT_DIR = BASE_DIR / "sentiment_analyzer" / "output" / "sentiment_reports"
DATA_DIR        = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Run daily MeLLeA trading pipeline")
parser.add_argument("--mock",   action="store_true",
                    help="Run in offline mock mode — no LLM calls, uses cached/synthetic data")
parser.add_argument("--output", default=str(DATA_DIR / "pipeline_output.json"),
                    help="Path to write pipeline_output.json")
parser.add_argument("--budget", type=float, default=2500.0,
                    help="Total portfolio budget (default: 2500)")
args = parser.parse_args()

MOCK_MODE   = args.mock
OUTPUT_PATH = Path(args.output)
BUDGET      = args.budget

# ── Conditionally import MeLLeA (skipped in mock mode) ───────────────────────
if not MOCK_MODE:
    try:
        import mellea
        from mellea_agents import (
            select_candidates,
            interpret_forecast,
            interpret_sentiment,
            interpret_backtest,
            daily_advisor,
        )
        mellea.configure(
            backend  = os.getenv("MELLEA_BACKEND", "openai"),
            model    = os.getenv("MELLEA_MODEL",   "gpt-4o-mini"),
            api_key  = os.getenv("OPENAI_API_KEY") or os.getenv("IBM_API_KEY"),
        )
        log.info(f"MeLLeA configured: backend={os.getenv('MELLEA_BACKEND','openai')}")
    except ImportError as e:
        log.error(f"MeLLeA import failed: {e}. Run with --mock for offline testing.")
        sys.exit(1)

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_forecast_json(ticker: str) -> Path | None:
    """Find the most recent forecast JSON for a ticker."""
    candidates = list(FORECASTS_DIR.glob(f"{ticker}_forecast_report.json"))
    if not candidates:
        # also check time_series_analyzer/output/
        candidates = list((BASE_DIR / "time_series_analyzer" / "output").glob(
            f"{ticker}_forecast_report.json"))
    return candidates[0] if candidates else None


def find_sentiment_report(ticker: str) -> Path | None:
    """Find the most recent sentiment report JSON or TXT for a ticker."""
    jsons = sorted(SENT_OUTPUT_DIR.glob(f"{ticker}_sentiment_report_*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if jsons:
        return jsons[0]
    txts = sorted(SENT_OUTPUT_DIR.glob(f"{ticker}_sentiment_report_*.txt"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    return txts[0] if txts else None


def load_backtest_json(ticker: str) -> dict | None:
    """Load existing backtest JSON or trigger a fresh run."""
    path = OUTCOMES_DIR / f"{ticker}_stage2_backtest.json"
    if path.exists():
        return load_json(path)
    log.info(f"No backtest for {ticker} — running stage2_backtest.py ...")
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "stage2_backtest.py"),
         "--ticker", ticker, "--capital", str(BUDGET / 5)],
        capture_output=True, text=True, cwd=str(BASE_DIR)
    )
    if result.returncode != 0:
        log.warning(f"stage2_backtest failed for {ticker}: {result.stderr[:200]}")
        return None
    return load_json(path) if path.exists() else None


# ── Mock data factory (for --mock / localhost UI testing) ────────────────────

def make_mock_output() -> dict:
    """Return a realistic synthetic pipeline_output.json for UI testing."""
    log.info("MOCK MODE — generating synthetic pipeline output")
    tickers = ["AMGN", "JNJ", "MU", "META", "C"]
    return {
        "date":             datetime.now().strftime("%Y-%m-%d"),
        "mode":             "mock",
        "budget":           BUDGET,
        "cash_remaining":   BUDGET - 1875.0,
        "tickers_to_buy":   ["AMGN"],
        "tickers_to_sell":  [],
        "tickers_to_hold":  ["JNJ", "MU"],
        "tickers_to_monitor": ["META", "C"],
        "stop_loss_orders": {"JNJ": 233.80, "MU": 87.40},
        "combined_scores":  {"AMGN": 74.2, "JNJ": 71.8, "MU": 68.5,
                             "META": 61.0, "C": 58.3},
        "user_prompt": (
            "Good morning! Today's top action is to BUY AMGN — the XGBoost "
            "forecast shows +8.2% upside over 30 days and the backtest Sharpe "
            "is 0.79. Hold your JNJ and MU positions with trailing stops at "
            "$233.80 and $87.40 respectively. You have $625.00 cash remaining "
            "of your $2,500 budget. No sells are recommended today."
        ),
        "all_tickers": tickers,
        "forecast": {
            t: {
                "ticker": t,
                "current_price": {"AMGN":385.95,"JNJ":252.07,"MU":112.40,
                                  "META":565.20,"C":68.90}[t],
                "target_price": {"AMGN":416.8,"JNJ":267.5,"MU":118.2,
                                 "META":551.0,"C":71.3}[t],
                "predicted_return_pct": {"AMGN":8.0,"JNJ":6.1,"MU":5.2,
                                         "META":-2.5,"C":3.5}[t],
                "forecast_trend": {"AMGN":"bullish","JNJ":"bullish",
                                   "MU":"bullish","META":"bearish","C":"neutral"}[t],
                "model_confidence": {"AMGN":0.82,"JNJ":0.79,"MU":0.71,
                                     "META":0.68,"C":0.75}[t],
                "trend_strength": {"AMGN":"strong","JNJ":"moderate","MU":"moderate",
                                   "META":"weak","C":"moderate"}[t],
                "recommendation": {"AMGN":"include","JNJ":"include","MU":"include",
                                   "META":"exclude","C":"include"}[t],
                "reasoning": "Based on XGBoost 30-day forecast and model metrics.",
                "forecast_results": [],   # full series loaded from JSON if needed
            }
            for t in tickers
        },
        "sentiment": {
            t: {
                "ticker": t,
                "sentiment_score": {"AMGN":65.6,"JNJ":72.1,"MU":68.3,
                                    "META":55.0,"C":61.8}[t],
                "sentiment_label": {"AMGN":"neutral","JNJ":"bullish","MU":"neutral",
                                    "META":"neutral","C":"neutral"}[t],
                "analyst_rating": {"AMGN":"hold","JNJ":"buy","MU":"buy",
                                   "META":"hold","C":"hold"}[t],
                "confidence": {"AMGN":0.62,"JNJ":0.74,"MU":0.69,
                               "META":0.58,"C":0.65}[t],
                "risk_level": {"AMGN":"high","JNJ":"medium","MU":"medium",
                               "META":"medium","C":"low"}[t],
                "position_multiplier": {"AMGN":0.80,"JNJ":1.10,"MU":1.0,
                                        "META":1.0,"C":1.0}[t],
                "key_risks": ["Pipeline uncertainty", "Market competition"],
                "recommendation": "include",
            }
            for t in tickers
        },
        "backtest": {
            t: {
                "ticker": t,
                "stage2_pass": True,
                "recommended_stop_label": {"AMGN":"2.5xATR (7.21%)","JNJ":"3.0xATR (7.49%)",
                                           "MU":"4.0%","META":"2.5%","C":"5.0%"}[t],
                "recommended_stop_pct": {"AMGN":7.21,"JNJ":7.49,"MU":4.0,
                                         "META":2.5,"C":5.0}[t],
                "sharpe_at_recommended": {"AMGN":0.787,"JNJ":0.950,"MU":0.685,
                                          "META":0.682,"C":0.730}[t],
                "mean_annual_return_pct": {"AMGN":13.66,"JNJ":16.48,"MU":8.91,
                                           "META":4.34,"C":9.37}[t],
                "p_loss_gt5_pct": {"AMGN":0.20,"JNJ":0.09,"MU":0.0,
                                   "META":0.0,"C":0.0}[t],
                "avg_stops_per_year": {"AMGN":8.5,"JNJ":4.7,"MU":42.4,
                                      "META":45.1,"C":11.9}[t],
                "is_high_volatility": False,
                "stop_dollar_amount": {"AMGN":27.82,"JNJ":18.87,"MU":4.50,
                                       "META":14.13,"C":3.45}[t],
                "portfolio_action": "include_with_stop",
                "position_size_advice": f"Allocate ~$500 of $2500 budget to {t}.",
            }
            for t in tickers
        },
        "actions_by_ticker": {
            "AMGN": "buy", "JNJ": "hold", "MU": "hold",
            "META": "monitor", "C": "monitor"
        },
    }


# ── Live pipeline stages ───────────────────────────────────────────────────────

def run_live_pipeline() -> dict:
    """Full live pipeline: screen → forecast → sentiment → backtest → advise."""

    # Add existing module paths
    sys.path.insert(0, str(BASE_DIR))
    sys.path.insert(0, str(BASE_DIR / "time_series_analyzer" / "src"))
    sys.path.insert(0, str(BASE_DIR / "sentiment_analyzer"))

    # ── Stage 0: Screen candidates ───────────────────────────────────────────
    log.info("Stage 0: Screening S&P500 candidates...")
    from generate_candidates import generate_candidates
    raw = generate_candidates(
        selected_sectors=["Technology", "Healthcare", "Financial Services"],
        num_candidates=7
    )
    screen_summary = "\n".join([
        f"{t}: score={s:.2f}, P/E={f['pe_ratio']:.1f}, "
        f"margin={f['profit_margin']*100:.1f}%, price=${f['current_price']:.2f}"
        for t, s, f in raw
    ])

    # ── Stage 1: MeLLeA candidate selection ──────────────────────────────────
    log.info("Stage 1: MeLLeA candidate selection...")
    candidates = select_candidates(sector_screen_summary=screen_summary, budget=BUDGET)
    tickers    = candidates.tickers
    log.info(f"  Selected: {tickers}")

    output = {
        "date":        datetime.now().strftime("%Y-%m-%d"),
        "mode":        "live",
        "budget":      BUDGET,
        "all_tickers": tickers,
        "forecast":    {},
        "sentiment":   {},
        "backtest":    {},
        "actions_by_ticker": {},
    }

    # ── Stage 2: Forecasts ────────────────────────────────────────────────────
    log.info("Stage 2: XGBoost forecasts + MeLLeA interpretation...")
    for ticker in tickers:
        fpath = find_forecast_json(ticker)
        if fpath:
            fd = interpret_forecast(ticker=ticker, forecast_json=fpath.read_text())
        else:
            log.warning(f"  No forecast JSON for {ticker} — running analyzer...")
            from main_analyzer import TimeSeriesAnalyzer
            analyzer = TimeSeriesAnalyzer(ticker, interactive=False)
            result   = analyzer.run_analysis(method="xgboost",
                                             features=["close", "volume"])
            if result:
                fd = interpret_forecast(ticker=ticker,
                                        forecast_json=json.dumps(result["forecast"]))
            else:
                log.warning(f"  Forecast failed for {ticker} — skipping")
                continue
        output["forecast"][ticker] = fd.model_dump()

    # ── Stage 3: Sentiment ────────────────────────────────────────────────────
    log.info("Stage 3: Sentiment analysis + MeLLeA interpretation...")
    for ticker in tickers:
        rpath = find_sentiment_report(ticker)
        if rpath:
            sig = interpret_sentiment(ticker=ticker,
                                      sentiment_report=rpath.read_text(encoding="utf-8",
                                                                        errors="ignore"))
        else:
            log.warning(f"  No sentiment report for {ticker} — running analyzer...")
            from src.sentiment_engine import SentimentEngine
            pdf = ANALYST_DIR / f"Analyst_{ticker}.pdf"
            if pdf.exists():
                engine = SentimentEngine(model_name="finbert")
                raw_result = engine.analyze_report(str(pdf))
                if raw_result["success"]:
                    sig = interpret_sentiment(ticker=ticker,
                                              sentiment_report=json.dumps(raw_result))
                else:
                    log.warning(f"  Sentiment analysis failed for {ticker} — skipping")
                    continue
            else:
                log.warning(f"  No analyst PDF for {ticker} — skipping sentiment")
                continue
        output["sentiment"][ticker] = sig.model_dump()

    # ── Stage 4: Backtests ────────────────────────────────────────────────────
    log.info("Stage 4: Loading backtest results + MeLLeA interpretation...")
    for ticker in tickers:
        bt_data = load_backtest_json(ticker)
        if bt_data:
            bs = interpret_backtest(ticker=ticker,
                                    backtest_data=json.dumps(bt_data, indent=2))
            output["backtest"][ticker] = bs.model_dump()

    # ── Stage 5: Daily advisor ────────────────────────────────────────────────
    log.info("Stage 5: MeLLeA daily advisor (majority voting)...")
    action = daily_advisor(
        portfolio_status = "No existing positions",
        forecast_decisions = json.dumps({t: output["forecast"].get(t, {})
                                         for t in tickers}, indent=2),
        sentiment_signals  = json.dumps({t: output["sentiment"].get(t, {})
                                         for t in tickers}, indent=2),
        backtest_signals   = json.dumps({t: output["backtest"].get(t, {})
                                         for t in tickers}, indent=2),
        cash_available     = BUDGET,
        today_date         = datetime.now().strftime("%Y-%m-%d"),
    )

    output.update({
        "cash_remaining":     action.cash_remaining,
        "tickers_to_buy":     action.tickers_to_buy,
        "tickers_to_sell":    action.tickers_to_sell,
        "tickers_to_hold":    action.tickers_to_hold,
        "tickers_to_monitor": action.tickers_to_monitor,
        "stop_loss_orders":   action.stop_loss_orders,
        "combined_scores":    action.combined_scores,
        "user_prompt":        action.user_prompt,
        "actions_by_ticker":  {
            **{t: "buy"     for t in action.tickers_to_buy},
            **{t: "sell"    for t in action.tickers_to_sell},
            **{t: "hold"    for t in action.tickers_to_hold},
            **{t: "monitor" for t in action.tickers_to_monitor},
        },
    })
    return output


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info(f"=== Daily Pipeline {'(MOCK)' if MOCK_MODE else '(LIVE)'} — "
             f"{datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    output = make_mock_output() if MOCK_MODE else run_live_pipeline()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    log.info(f"Pipeline complete. Output: {OUTPUT_PATH}")
    print(f"\n[OK] Pipeline output written to: {OUTPUT_PATH}")
    print(f"  Tickers: {output.get('all_tickers', [])}")
    print(f"  Buy:     {output.get('tickers_to_buy', [])}")
    print(f"  Hold:    {output.get('tickers_to_hold', [])}")
    print(f"  Cash:    ${output.get('cash_remaining', 0):.2f}")


if __name__ == "__main__":
    main()

# Made with Bob
