"""
run_jnj.py — Run the full Mellea pipeline for JNJ only.
=========================================================
Bypasses the S&P500 screener (Stage 0/1) and drives all
data-generation + Mellea interpretation stages for JNJ:

  1. XGBoost forecast  (generates or reuses time_series_analyzer/output/JNJ_forecast_report.json)
  2. Stage 2 backtest  (generates or reuses Analysis_Outcomes/JNJ_stage2_backtest.json)
  3. Mellea: interpret_forecast()
  4. Mellea: interpret_sentiment()   (skipped if no analyst PDF/report)
  5. Mellea: interpret_backtest()
  6. Mellea: daily_advisor()
  7. Write data/jnj_pipeline_output.json

Usage:
    cd stock-trading-system
    python run_jnj.py
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ── Bootstrap: load .env first ────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

BASE_DIR      = Path(__file__).parent
DATA_DIR      = BASE_DIR / "data"
FORECASTS_DIR = BASE_DIR / "time_series_analyzer" / "output"
OUTCOMES_DIR  = BASE_DIR / "Analysis_Outcomes"
SENT_OUT_DIR  = BASE_DIR / "sentiment_analyzer" / "output" / "sentiment_reports"
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(DATA_DIR / "jnj_pipeline.log"), mode="w"),
    ],
)
log = logging.getLogger(__name__)

TICKER = "JNJ"
BUDGET = 2500.0

# ── Configure Mellea ──────────────────────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "time_series_analyzer" / "src"))

import mellea_shim as mellea
from mellea_agents import (
    interpret_forecast,
    interpret_sentiment,
    interpret_backtest,
    daily_advisor,
)

mellea.configure(
    backend = os.getenv("MELLEA_BACKEND", "ollama"),
    model   = os.getenv("MELLEA_MODEL",   "llama3"),
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("IBM_API_KEY"),
)
log.info(f"Mellea configured: backend={os.getenv('MELLEA_BACKEND','ollama')} "
         f"model={os.getenv('MELLEA_MODEL','llama3')}")


# ── Stage 1: XGBoost forecast ─────────────────────────────────────────────────
def run_forecast() -> Path:
    """Run XGBoost forecast for JNJ; return path to the JSON report."""
    json_path = FORECASTS_DIR / f"{TICKER}_forecast_report.json"

    # Check if a valid xgboost forecast already exists
    if json_path.exists():
        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
            if (meta.get("selected_method") or "").lower() == "xgboost":
                log.info(f"Reusing cached XGBoost forecast: {json_path}")
                return json_path
            else:
                log.info(f"Cached forecast is '{meta.get('selected_method')}' — regenerating with xgboost.")
        except Exception:
            pass

    log.info("Running XGBoost forecast via time_series_analyzer ...")
    from main_analyzer import TimeSeriesAnalyzer
    analyzer = TimeSeriesAnalyzer(TICKER, interactive=False)
    result   = analyzer.run_analysis(method="xgboost", features=["close", "volume"])
    if not result:
        raise RuntimeError(f"XGBoost forecast failed for {TICKER}")
    if not json_path.exists():
        raise RuntimeError(f"Forecast JSON not written to expected path: {json_path}")
    log.info(f"Forecast complete: {json_path}")
    return json_path


# ── Stage 2: ATR backtest ─────────────────────────────────────────────────────
def run_backtest() -> Path:
    """Run Stage 2 ATR backtest for JNJ; return path to the JSON output."""
    json_path = OUTCOMES_DIR / f"{TICKER}_stage2_backtest.json"
    if json_path.exists():
        log.info(f"Reusing cached backtest: {json_path}")
        return json_path

    log.info("Running Stage 2 ATR backtest ...")
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "stage2_backtest.py"),
         "--ticker", TICKER, "--capital", "500"],
        capture_output=False, text=True, cwd=str(BASE_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError(f"stage2_backtest.py failed for {TICKER}")
    if not json_path.exists():
        raise RuntimeError(f"Backtest JSON not written to expected path: {json_path}")
    log.info(f"Backtest complete: {json_path}")
    return json_path


# ── Helpers ───────────────────────────────────────────────────────────────────
def slim_forecast_json(path: Path) -> str:
    """Return a compact forecast summary (~1 KB) instead of the full 267 KB JSON.

    The full report contains 251 rows of raw historical OHLCV data which burns
    tokens without adding signal.  Mellea only needs the summary fields.
    """
    full = json.loads(path.read_text(encoding="utf-8"))
    forecasts = full.get("forecast_results", [])
    target_price = round(forecasts[-1]["forecast"], 2) if forecasts else None
    first_price  = round(forecasts[0]["forecast"],  2) if forecasts else None
    summary = {
        "ticker":          full.get("metadata", {}).get("ticker"),
        "company_name":    full.get("metadata", {}).get("company_name"),
        "selected_method": full.get("selected_method"),
        "forecast_start":  full.get("metadata", {}).get("forecast_start_date"),
        "forecast_end":    full.get("metadata", {}).get("forecast_end_date"),
        "forecast_periods": full.get("metadata", {}).get("forecast_periods"),
        "current_metrics": full.get("current_metrics"),
        "data_characteristics": full.get("data_characteristics"),
        "forecast_summary": full.get("forecast_summary"),
        "model_metrics":   full.get("model_metrics"),
        "forecast_first":  first_price,
        "forecast_last":   target_price,
        # include last 5 forecast rows so Mellea can see direction
        "forecast_tail":   [
            {"date": r["date"], "forecast": round(r["forecast"], 2)}
            for r in forecasts[-5:]
        ],
    }
    return json.dumps(summary, indent=2, default=str)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info(f"=== JNJ Mellea Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    # 1. Generate / load forecast
    forecast_path = run_forecast()
    forecast_text = slim_forecast_json(forecast_path)
    log.info(f"Forecast summary size: {len(forecast_text)} chars (was {forecast_path.stat().st_size // 1024} KB)")

    # 2. Generate / load backtest
    backtest_path = run_backtest()
    backtest_text = backtest_path.read_text(encoding="utf-8")

    # 3. Mellea: interpret forecast
    log.info("Mellea Stage 3: interpret_forecast ...")
    fd = interpret_forecast(ticker=TICKER, forecast_json=forecast_text)
    log.info(f"  Forecast: trend={fd.forecast_trend}  return={fd.predicted_return_pct:+.1f}%  "
             f"confidence={fd.model_confidence:.2f}  rec={fd.recommendation}")

    # 4. Mellea: interpret sentiment
    sig = None
    ANALYST_DIR = BASE_DIR / "sentiment_analyzer" / "Analyst_reports"

    # Check for a pre-generated sentiment JSON first (fastest path)
    sent_reports = sorted(SENT_OUT_DIR.glob(f"{TICKER}_sentiment_report_*.json"),
                          key=lambda p: p.stat().st_mtime, reverse=True)

    if sent_reports:
        log.info("Mellea Stage 4: interpret_sentiment (from cached JSON) ...")
        raw_sentiment = sent_reports[0].read_text(encoding="utf-8", errors="ignore")
    else:
        # Find analyst PDF case-insensitively (file may be Analyst_jnj.pdf or Analyst_JNJ.pdf)
        pdf_matches = [p for p in ANALYST_DIR.iterdir()
                       if p.suffix.lower() == ".pdf"
                       and p.stem.lower() == f"analyst_{TICKER.lower()}"]
        if pdf_matches:
            pdf_path = pdf_matches[0]
            log.info(f"Running FinBERT sentiment on {pdf_path.name} ...")
            sys.path.insert(0, str(BASE_DIR / "sentiment_analyzer"))
            from src.sentiment_engine import SentimentEngine
            engine = SentimentEngine(model_name="finbert")
            raw_result = engine.analyze_report(str(pdf_path))
            if not raw_result.get("success"):
                log.warning(f"Sentiment analysis failed: {raw_result.get('error')} — skipping.")
                raw_sentiment = None
            else:
                raw_sentiment = json.dumps(raw_result, indent=2)
                # Cache for future runs
                SENT_OUT_DIR.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                cache_path = SENT_OUT_DIR / f"{TICKER}_sentiment_report_{ts}.json"
                cache_path.write_text(raw_sentiment, encoding="utf-8")
                log.info(f"Sentiment report cached: {cache_path.name}")
        else:
            log.warning(f"No analyst PDF found for {TICKER} in {ANALYST_DIR} — skipping sentiment.")
            raw_sentiment = None

    if raw_sentiment:
        log.info("Mellea Stage 4: interpret_sentiment ...")
        sig = interpret_sentiment(ticker=TICKER, sentiment_report=raw_sentiment)
        log.info(f"  Sentiment: score={sig.sentiment_score:.1f}  label={sig.sentiment_label}  "
                 f"rating={sig.analyst_rating}  rec={sig.recommendation}")

    # 5. Mellea: interpret backtest
    log.info("Mellea Stage 5: interpret_backtest ...")
    bs = interpret_backtest(ticker=TICKER, backtest_data=backtest_text)
    log.info(f"  Backtest: pass={bs.stage2_pass}  stop={bs.recommended_stop_label}  "
             f"sharpe={bs.sharpe_at_recommended:.3f}  action={bs.portfolio_action}")

    # 6. Mellea: daily advisor
    log.info("Mellea Stage 6: daily_advisor ...")
    action = daily_advisor(
        portfolio_status   = "No existing positions",
        forecast_decisions = json.dumps({TICKER: fd.model_dump()},   indent=2),
        sentiment_signals  = json.dumps({TICKER: sig.model_dump() if sig else {}}, indent=2),
        backtest_signals   = json.dumps({TICKER: bs.model_dump()},   indent=2),
        cash_available     = BUDGET,
        today_date         = datetime.now().strftime("%Y-%m-%d"),
    )

    # 7. Write output
    output = {
        "date":               datetime.now().strftime("%Y-%m-%d"),
        "ticker":             TICKER,
        "budget":             BUDGET,
        "forecast":           fd.model_dump(),
        "sentiment":          sig.model_dump() if sig else None,
        "backtest":           bs.model_dump(),
        "tickers_to_buy":     action.tickers_to_buy,
        "tickers_to_sell":    action.tickers_to_sell,
        "tickers_to_hold":    action.tickers_to_hold,
        "tickers_to_monitor": action.tickers_to_monitor,
        "stop_loss_orders":   action.stop_loss_orders,
        "cash_remaining":     action.cash_remaining,
        "combined_scores":    action.combined_scores,
        "user_prompt":        action.user_prompt,
    }
    out_path = DATA_DIR / "jnj_pipeline_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print(f"  JNJ Pipeline Complete")
    print("=" * 60)
    print(f"  Forecast  : {fd.forecast_trend}  {fd.predicted_return_pct:+.1f}%  rec={fd.recommendation}")
    print(f"  Backtest  : {'PASS' if bs.stage2_pass else 'FAIL'}  stop={bs.recommended_stop_label}  sharpe={bs.sharpe_at_recommended:.3f}")
    if sig:
        print(f"  Sentiment : {sig.sentiment_label}  score={sig.sentiment_score:.0f}  rating={sig.analyst_rating}")
    print(f"  Action    : buy={action.tickers_to_buy}  hold={action.tickers_to_hold}  monitor={action.tickers_to_monitor}")
    print(f"  Stop loss : {action.stop_loss_orders}")
    print(f"  Cash left : ${action.cash_remaining:.2f}")
    print(f"\n  Briefing  :\n  {action.user_prompt}")
    print(f"\n  Output    : {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()

# Made with IBM Bob
