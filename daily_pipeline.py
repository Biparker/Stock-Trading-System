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
from datetime import datetime, timedelta
from pathlib import Path

# Load .env before anything else so env vars are in os.environ
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

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
POSITIONS_FILE  = DATA_DIR / "positions.json"

# ── Forecast cache policy ─────────────────────────────────────────────────────
MAX_FORECAST_AGE_DAYS = 5     # Rerun XGBoost after 5 calendar days (per operator instructions §3)

# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Run daily MeLLeA trading pipeline")
parser.add_argument("--mock",   action="store_true",
                    help="Run in offline mock mode — no LLM calls, uses cached/synthetic data")
parser.add_argument("--output", default=str(DATA_DIR / "pipeline_output.json"),
                    help="Path to write pipeline_output.json")
parser.add_argument("--budget", type=float, default=2500.0,
                    help="Total portfolio budget (default: 2500)")
parser.add_argument("--tickers", nargs="+", default=None,
                    help="Skip screening — run pipeline with this exact list of tickers, "
                         "e.g. --tickers NVDA META AAPL CRM JNJ QCOM BMY")
args = parser.parse_args()

MOCK_MODE     = args.mock
OUTPUT_PATH   = Path(args.output)
BUDGET        = args.budget
FIXED_TICKERS = args.tickers  # None means run normal screener (per operator instructions §4)

# ── Event Calendar Guard ─────────────────────────────────────────────────────
from earnings_calendar_guard import EarningsCalendarGuard

# ── Conditionally import MeLLeA (skipped in mock mode) ───────────────────────
if not MOCK_MODE:
    try:
        import mellea_shim as mellea
        from mellea_agents import (
            select_candidates,
            interpret_forecast,
            interpret_sentiment,
            interpret_backtest,
            daily_advisor,
        )
        mellea.configure(
            backend  = os.getenv("MELLEA_BACKEND", "ollama"),
            model    = os.getenv("MELLEA_MODEL",   "llama3"),
            api_key  = os.getenv("OPENAI_API_KEY") or os.getenv("IBM_API_KEY"),
        )
        log.info(f"mellea_shim configured: backend={os.getenv('MELLEA_BACKEND','ollama')}, model={os.getenv('MELLEA_MODEL','llama3')}")
    except ImportError as e:
        log.error(f"MeLLeA import failed: {e}. Run with --mock for offline testing.")
        sys.exit(1)

# ── Helpers ───────────────────────────────────────────────────────────────────

import numpy as _np

class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy scalars and arrays from the time-series analyzer."""
    def default(self, obj):
        if isinstance(obj, _np.ndarray):
            return obj.tolist()
        if isinstance(obj, _np.integer):
            return int(obj)
        if isinstance(obj, _np.floating):
            return float(obj)
        return super().default(obj)


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_positions() -> dict:
    """Load persisted portfolio positions from positions.json.

    Returns an empty dict (no positions) if the file doesn't exist yet.
    Schema mirrors the stop_loss_orders dict: {ticker: stop_price_dollars, ...}
    Extended with an 'open_positions' key: {ticker: {shares, cost_basis, stop}}.
    """
    if POSITIONS_FILE.exists():
        try:
            return load_json(POSITIONS_FILE)
        except Exception as e:
            log.warning(f"Could not read positions.json: {e} — starting fresh")
    return {"open_positions": {}, "stop_loss_orders": {}}


def save_positions(action_output: dict) -> None:
    """Persist today's positions to positions.json for the next pipeline run.

    Reads tickers_to_buy, tickers_to_sell, tickers_to_hold, and stop_loss_orders
    from action_output and writes an updated positions snapshot.
    """
    existing = load_positions()
    open_pos  = dict(existing.get("open_positions", {}))

    # Remove sold positions
    for t in action_output.get("tickers_to_sell", []):
        open_pos.pop(t, None)

    # Add newly bought positions (price from backtest data embedded in output)
    for t in action_output.get("tickers_to_buy", []):
        bt = action_output.get("backtest", {}).get(t, {})
        fc = action_output.get("forecast", {}).get(t, {})
        open_pos[t] = {
            "shares":     None,           # filled in manually after execution
            "cost_basis": fc.get("current_price"),
            "stop":       bt.get("stop_dollar_amount"),
            "added_date": action_output.get("date"),
        }

    # Update stop prices for held positions
    stops = action_output.get("stop_loss_orders", {})
    for t, stop_price in stops.items():
        if t in open_pos:
            open_pos[t]["stop"] = stop_price

    snapshot = {
        "as_of":          action_output.get("date"),
        "open_positions": open_pos,
        "stop_loss_orders": stops,
    }
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, default=str)
    log.info(f"Positions saved to {POSITIONS_FILE} ({len(open_pos)} open positions)")


def _neutral_sentiment(ticker: str):
    """Return a neutral SentimentSignal when no analyst PDF is available.

    Uses recommendation='include' with a neutral score (50) and medium risk so
    it does not block the buy gate while clearly flagging the absence of real data.
    """
    from mellea_schemas import SentimentSignal
    return SentimentSignal(
        ticker=ticker,
        sentiment_score=50.0,
        sentiment_label="neutral",
        analyst_rating="unknown",
        confidence=0.0,
        risk_level="medium",
        position_multiplier=1.0,
        key_risks=["No analyst report available — sentiment is synthetic neutral"],
        recommendation="include",
    )


def compute_combined_scores(
    forecast: dict,
    sentiment: dict,
    tickers: list,
) -> dict:
    """Compute combined scores deterministically in Python — not inside the LLM.

    Formula: (forecast_confidence × 0.60 + sentiment_score/100 × 0.40) × 100
    Falls back to forecast_confidence × 60 if sentiment is missing for a ticker.
    """
    scores = {}
    for t in tickers:
        fc_conf = forecast.get(t, {}).get("model_confidence", 0.0)
        sent_score = sentiment.get(t, {}).get("sentiment_score", 50.0)
        scores[t] = round((fc_conf * 0.60 + sent_score / 100 * 0.40) * 100, 2)
    return scores


def find_forecast_json(ticker: str) -> Path | None:
    """Find the most recent XGBoost forecast JSON for a ticker.

    Returns None (triggering a fresh run) if:
    - no cached file exists, or
    - the cached file was not produced by the xgboost method, or
    - the cached file is older than MAX_FORECAST_AGE_DAYS calendar days.
    """
    candidates = list(FORECASTS_DIR.glob(f"{ticker}_forecast_report.json"))
    if not candidates:
        # also check time_series_analyzer/output/
        candidates = list((BASE_DIR / "time_series_analyzer" / "output").glob(
            f"{ticker}_forecast_report.json"))
    if not candidates:
        return None

    path = candidates[0]
    try:
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        method = meta.get("selected_method") or meta.get("method", "")
        if method.lower() != "xgboost":
            log.warning(
                f"Cached forecast for {ticker} used method '{method}' — "
                "regenerating with xgboost."
            )
            return None
    except Exception as e:
        log.warning(f"Could not read cached forecast for {ticker}: {e} — regenerating.")
        return None

    # Staleness check — reject files older than MAX_FORECAST_AGE_DAYS
    age_days = (datetime.now().timestamp() - path.stat().st_mtime) / 86400
    if age_days > MAX_FORECAST_AGE_DAYS:
        log.warning(
            f"Cached forecast for {ticker} is {age_days:.1f} days old "
            f"(limit {MAX_FORECAST_AGE_DAYS} days) — regenerating with xgboost."
        )
        return None

    return path


def find_sentiment_report(ticker: str) -> Path | None:
    """Find the most recent cached sentiment report JSON or TXT for a ticker.

    Returns None (forcing a fresh PDF re-analysis) if a PDF in ANALYST_DIR
    is newer than the most recent cached report, so newly uploaded analyst
    reports are always picked up on the next pipeline run.
    """
    candidates = (
        sorted(SENT_OUTPUT_DIR.glob(f"{ticker}_sentiment_report_*.json"),
               key=lambda p: p.stat().st_mtime, reverse=True)
        + sorted(SENT_OUTPUT_DIR.glob(f"{ticker}_sentiment_report_*.txt"),
                 key=lambda p: p.stat().st_mtime, reverse=True)
    )
    if not candidates:
        return None
    cached = max(candidates, key=lambda p: p.stat().st_mtime)

    # Check whether a fresher PDF has been uploaded since this cache was written.
    # Patterns cover exact name, date-suffixed name (e.g. Analyst_CRM_090526.pdf),
    # and all case variants so mixed-case filenames (e.g. Analyst_jnj_082126.pdf) are found.
    pdf_matches = (
        list(ANALYST_DIR.glob(f"Analyst_{ticker}.pdf"))
        + list(ANALYST_DIR.glob(f"Analyst_{ticker}_*.pdf"))
        + list(ANALYST_DIR.glob(f"Analyst_{ticker.lower()}.pdf"))
        + list(ANALYST_DIR.glob(f"Analyst_{ticker.lower()}_*.pdf"))
        + list(ANALYST_DIR.glob(f"Analyst_{ticker.upper()}.pdf"))
        + list(ANALYST_DIR.glob(f"Analyst_{ticker.upper()}_*.pdf"))
    )
    if pdf_matches:
        pdf = max(pdf_matches, key=lambda p: p.stat().st_mtime)
        if pdf.stat().st_mtime > cached.stat().st_mtime:
            log.info(
                f"  Fresh PDF for {ticker} ({pdf.name}) is newer than cached "
                f"sentiment report ({cached.name}) — re-running analysis."
            )
            return None

    return cached


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
    tickers = ["NVDA", "META", "AAPL", "CRM", "JNJ", "QCOM", "BMY"]
    return {
        "date":             datetime.now().strftime("%Y-%m-%d"),
        "mode":             "mock",
        "budget":           BUDGET,
        "cash_remaining":   BUDGET - 1875.0,
        "tickers_to_buy":   ["NVDA", "CRM"],
        "tickers_to_sell":  [],
        "tickers_to_hold":  ["JNJ", "AAPL"],
        "tickers_to_monitor": ["META", "QCOM", "BMY"],
        "stop_loss_orders": {"JNJ": 248.20, "AAPL": 291.35},
        "combined_scores":  {"NVDA": 88.5, "META": 72.1, "AAPL": 79.4,
                             "CRM": 81.2, "JNJ": 74.6, "QCOM": 68.3, "BMY": 61.9},
        "user_prompt": (
            "Good morning! Today's top actions are to BUY NVDA and CRM — both "
            "show strong XGBoost upside and bullish analyst sentiment. Hold JNJ "
            "and AAPL with trailing stops at $248.20 and $291.35. Monitor META, "
            "QCOM, and BMY for entry opportunities. You have $625.00 cash "
            "remaining of your $2,500 budget."
        ),
        "all_tickers": tickers,
        "forecast": {
            t: {
                "ticker": t,
                "current_price": {"NVDA":226.06,"META":616.33,"AAPL":315.60,
                                  "CRM":248.18,"JNJ":268.61,"QCOM":175.16,"BMY":65.12}[t],
                "target_price":  {"NVDA":251.0,"META":628.0,"AAPL":331.4,
                                  "CRM":268.5,"JNJ":282.0,"QCOM":183.0,"BMY":68.5}[t],
                "predicted_return_pct": {"NVDA":11.0,"META":1.9,"AAPL":5.0,
                                         "CRM":8.2,"JNJ":5.0,"QCOM":4.5,"BMY":5.2}[t],
                "forecast_trend": {"NVDA":"bullish","META":"neutral","AAPL":"bullish",
                                   "CRM":"bullish","JNJ":"bullish","QCOM":"neutral","BMY":"neutral"}[t],
                "model_confidence": {"NVDA":0.87,"META":0.70,"AAPL":0.81,
                                     "CRM":0.79,"JNJ":0.76,"QCOM":0.72,"BMY":0.68}[t],
                "trend_strength": {"NVDA":"strong","META":"moderate","AAPL":"moderate",
                                   "CRM":"strong","JNJ":"moderate","QCOM":"moderate","BMY":"weak"}[t],
                "recommendation": {"NVDA":"include","META":"monitor","AAPL":"include",
                                   "CRM":"include","JNJ":"include","QCOM":"monitor","BMY":"monitor"}[t],
                "reasoning": "Based on XGBoost 30-day forecast and model metrics.",
                "forecast_results": [],
            }
            for t in tickers
        },
        "sentiment": {
            t: {
                "ticker": t,
                "sentiment_score": {"NVDA":82.0,"META":61.5,"AAPL":74.3,
                                    "CRM":78.1,"JNJ":70.2,"QCOM":63.8,"BMY":59.4}[t],
                "sentiment_label": {"NVDA":"bullish","META":"neutral","AAPL":"bullish",
                                    "CRM":"bullish","JNJ":"bullish","QCOM":"neutral","BMY":"neutral"}[t],
                "analyst_rating": {"NVDA":"buy","META":"hold","AAPL":"buy",
                                   "CRM":"buy","JNJ":"buy","QCOM":"hold","BMY":"hold"}[t],
                "confidence": {"NVDA":0.85,"META":0.63,"AAPL":0.78,
                               "CRM":0.80,"JNJ":0.74,"QCOM":0.65,"BMY":0.61}[t],
                "risk_level": {"NVDA":"medium","META":"medium","AAPL":"low",
                               "CRM":"medium","JNJ":"low","QCOM":"medium","BMY":"medium"}[t],
                "position_multiplier": {"NVDA":1.20,"META":1.0,"AAPL":1.10,
                                        "CRM":1.15,"JNJ":1.05,"QCOM":1.0,"BMY":0.90}[t],
                "key_risks": ["Market competition", "Macro headwinds"],
                "recommendation": "include",
            }
            for t in tickers
        },
        "backtest": {
            t: {
                "ticker": t,
                "stage2_pass": True,
                "recommended_stop_label": {"NVDA":"2.5xATR (8.10%)","META":"3.0xATR (7.20%)",
                                           "AAPL":"2.5xATR (6.50%)","CRM":"3.0xATR (7.80%)",
                                           "JNJ":"3.0xATR (7.49%)","QCOM":"2.5xATR (7.10%)",
                                           "BMY":"2.5xATR (6.20%)"}[t],
                "recommended_stop_pct": {"NVDA":8.10,"META":7.20,"AAPL":6.50,
                                         "CRM":7.80,"JNJ":7.49,"QCOM":7.10,"BMY":6.20}[t],
                "sharpe_at_recommended": {"NVDA":0.92,"META":0.75,"AAPL":0.88,
                                          "CRM":0.84,"JNJ":0.95,"QCOM":0.71,"BMY":0.68}[t],
                "mean_annual_return_pct": {"NVDA":22.4,"META":9.8,"AAPL":14.1,
                                           "CRM":16.5,"JNJ":11.2,"QCOM":10.3,"BMY":8.7}[t],
                "p_loss_gt5_pct": {"NVDA":0.12,"META":0.18,"AAPL":0.09,
                                   "CRM":0.14,"JNJ":0.08,"QCOM":0.17,"BMY":0.19}[t],
                "avg_stops_per_year": {"NVDA":6.2,"META":8.1,"AAPL":5.4,
                                       "CRM":7.3,"JNJ":4.7,"QCOM":7.8,"BMY":6.9}[t],
                "is_high_volatility": False,
                "stop_dollar_amount": {"NVDA":18.31,"META":44.37,"AAPL":20.51,
                                       "CRM":19.36,"JNJ":20.11,"QCOM":12.44,"BMY":4.04}[t],
                "portfolio_action": "include_with_stop",
                "position_size_advice": f"Allocate ~$357 of $2500 budget to {t}.",
            }
            for t in tickers
        },
        "actions_by_ticker": {
            "NVDA": "buy", "META": "monitor", "AAPL": "hold",
            "CRM": "buy", "JNJ": "hold", "QCOM": "monitor", "BMY": "monitor"
        },
        "signal_dates": {},
        "data_ages":    {},
    }


# ── Live pipeline stages ───────────────────────────────────────────────────────

def run_live_pipeline() -> dict:
    """Full live pipeline: screen → forecast → sentiment → backtest → advise."""

    # Add existing module paths
    sys.path.insert(0, str(BASE_DIR))
    sys.path.insert(0, str(BASE_DIR / "time_series_analyzer" / "src"))
    sys.path.insert(0, str(BASE_DIR / "sentiment_analyzer"))

    # ── Stage 0 / 1: Screen candidates or use fixed list ─────────────────────
    if FIXED_TICKERS:
        tickers = [t.upper() for t in FIXED_TICKERS]
        log.info(f"Stage 0/1: Using fixed ticker list (--tickers): {tickers}")
    else:
        log.info("Stage 0: Screening S&P500 candidates...")
        from generate_candidates import generate_candidates
        raw = generate_candidates(
            selected_sectors=["Technology", "Healthcare", "Financial Services"],
            num_candidates=7
        )
        # Build screened ticker set for hallucination guard
        screened_tickers = [t for t, s, f in raw]

        screen_summary = "\n".join([
            f"{t}: score={s:.2f}, P/E={f['pe_ratio']:.1f}, "
            f"margin={f['profit_margin']*100:.1f}%, price=${f['current_price']:.2f}, "
            f"atr_pct={f.get('atr_pct', 0):.2f}%, return_20d={f.get('return_20d', 0):+.2f}%"
            for t, s, f in raw
        ])

        # Append explicit allowlist so MeLLeA cannot hallucinate tickers
        screen_summary += (
            f"\n\nYOU MAY ONLY SELECT FROM THIS EXACT LIST: {screened_tickers}. "
            "Do not select any ticker not present in this list."
        )

        # ── Stage 1: MeLLeA candidate selection ──────────────────────────────
        log.info("Stage 1: MeLLeA candidate selection...")
        candidates = select_candidates(sector_screen_summary=screen_summary, budget=BUDGET)

        # ── Hallucination guard: drop any ticker not in the screened set ──────
        valid_tickers = [t for t in candidates.tickers if t in screened_tickers]
        hallucinated  = [t for t in candidates.tickers if t not in screened_tickers]
        if hallucinated:
            log.warning(
                f"  MeLLeA hallucinated tickers not in screened list: {hallucinated} — removed."
            )
        if not valid_tickers:
            log.warning("  All selected tickers were hallucinated — falling back to top screened tickers.")
            valid_tickers = screened_tickers[:3]

        tickers = valid_tickers
        log.info(f"  Selected (after guard): {tickers}")

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

    # Tracks data age (in days) for each ticker's signal sources.
    # Values are int days or "no file found" when the source file was absent.
    data_ages: dict = {}

    # Tracks the actual source dates for each ticker's signal files.
    # Written to pipeline_output.json so the HTML dashboard can display real freshness dates.
    signal_dates: dict = {}

    # ── Stage 2: Forecasts ────────────────────────────────────────────────────
    log.info("Stage 2: XGBoost forecasts + MeLLeA interpretation...")
    for ticker in tickers:
        fpath = find_forecast_json(ticker)
        if fpath:
            forecast_days = int((datetime.now().timestamp() - fpath.stat().st_mtime) / 86400)
            forecast_json_text = fpath.read_text()
            fd = interpret_forecast(ticker=ticker, forecast_json=forecast_json_text)
            # Extract forecast_start_date from the cached JSON metadata
            try:
                fmeta = json.loads(forecast_json_text)
                fsd = fmeta.get("metadata", {}).get("forecast_start_date", "")
                signal_dates.setdefault(ticker, {})["forecast_date"] = fsd[:10] if fsd else "unknown"
            except Exception:
                signal_dates.setdefault(ticker, {})["forecast_date"] = "unknown"
        else:
            forecast_days = "no file found"
            log.warning(f"  No forecast JSON for {ticker} — running analyzer...")
            from time_series_analyzer.src.main_analyzer import TimeSeriesAnalyzer
            analyzer = TimeSeriesAnalyzer(ticker, interactive=False)
            result   = analyzer.run_analysis(method="xgboost",
                                             features=["close", "volume"])
            if result:
                fd = interpret_forecast(ticker=ticker,
                                        forecast_json=json.dumps(result["forecast"],
                                                                  cls=_NumpyEncoder))
                # Extract forecast_start_date from the freshly-run result
                try:
                    fsd = result["forecast"].get("metadata", {}).get("forecast_start_date", "")
                    signal_dates.setdefault(ticker, {})["forecast_date"] = fsd[:10] if fsd else "unknown"
                except Exception:
                    signal_dates.setdefault(ticker, {})["forecast_date"] = "unknown"
            else:
                log.warning(f"  Forecast failed for {ticker} — skipping")
                signal_dates.setdefault(ticker, {})["forecast_date"] = "unknown"
                continue
        output["forecast"][ticker] = fd.model_dump()
        data_ages.setdefault(ticker, {})["forecast_days"] = forecast_days

    # ── Stage 3: Sentiment ────────────────────────────────────────────────────
    log.info("Stage 3: Sentiment analysis + MeLLeA interpretation...")
    for ticker in tickers:
        rpath = find_sentiment_report(ticker)
        if rpath:
            sentiment_days = int((datetime.now().timestamp() - rpath.stat().st_mtime) / 86400)
            report_text = rpath.read_text(encoding="utf-8", errors="ignore")
            sig = interpret_sentiment(ticker=ticker, sentiment_report=report_text)
            # Extract analysis_date from JSON reports; fall back to file mtime for .txt
            try:
                if rpath.suffix.lower() == ".json":
                    rdata = json.loads(report_text)
                    ad = rdata.get("analysis_date", "")
                    signal_dates.setdefault(ticker, {})["sentiment_date"] = ad[:10] if ad else "unknown"
                else:
                    signal_dates.setdefault(ticker, {})["sentiment_date"] = (
                        datetime.fromtimestamp(rpath.stat().st_mtime).strftime("%Y-%m-%d")
                    )
            except Exception:
                signal_dates.setdefault(ticker, {})["sentiment_date"] = "unknown"
        else:
            sentiment_days = "no file found"
            signal_dates.setdefault(ticker, {})["sentiment_date"] = "unknown"
            log.warning(f"  No sentiment report for {ticker} — running analyzer...")
            # Case-insensitive and date-suffix-aware PDF search
            # Covers Analyst_CRM.pdf, Analyst_CRM_090526.pdf, Analyst_crm_082126.pdf, etc.
            pdf_matches = (
                list(ANALYST_DIR.glob(f"Analyst_{ticker}.pdf"))
                + list(ANALYST_DIR.glob(f"Analyst_{ticker}_*.pdf"))
                + list(ANALYST_DIR.glob(f"Analyst_{ticker.lower()}.pdf"))
                + list(ANALYST_DIR.glob(f"Analyst_{ticker.lower()}_*.pdf"))
                + list(ANALYST_DIR.glob(f"Analyst_{ticker.upper()}.pdf"))
                + list(ANALYST_DIR.glob(f"Analyst_{ticker.upper()}_*.pdf"))
            )
            pdf = pdf_matches[0] if pdf_matches else None
            if pdf and pdf.exists():
                # Run FinBERT in a subprocess to avoid memory conflicts with
                # XGBoost/PyTorch/pandas already loaded in this process.
                # Use -m (module mode) so relative imports in sentiment_engine work.
                log.info(f"  Running FinBERT subprocess for {ticker}: {pdf.name}")
                proc = subprocess.run(
                    [sys.executable, "-m", "sentiment_analyzer.src.sentiment_engine",
                     str(pdf.resolve())],
                    capture_output=True, text=True,
                    cwd=str(BASE_DIR),
                    timeout=300,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    # Extract the JSON line from stdout (ignore any log lines)
                    json_line = next(
                        (l for l in proc.stdout.splitlines() if l.strip().startswith("{")),
                        None
                    )
                    if json_line:
                        raw_result = json.loads(json_line)
                    else:
                        raw_result = {"success": False, "error": "no JSON in subprocess output"}
                else:
                    raw_result = {"success": False, "error": proc.stderr[-500:] if proc.stderr else "subprocess failed"}
                if raw_result.get("success"):
                    sig = interpret_sentiment(ticker=ticker,
                                              sentiment_report=json.dumps(raw_result))
                    ad = raw_result.get("analysis_date", "")
                    signal_dates.setdefault(ticker, {})["sentiment_date"] = ad[:10] if ad else "unknown"
                    sentiment_days = 0  # just generated right now
                else:
                    log.warning(f"  Sentiment analysis failed for {ticker}: {raw_result.get('error','unknown')} — using neutral signal")
                    sig = _neutral_sentiment(ticker)
            else:
                log.warning(
                    f"  No analyst PDF for {ticker} — using neutral sentiment signal. "
                    f"Add Analyst_{ticker}.pdf to sentiment_analyzer/Analyst_reports/ for real analysis."
                )
                sig = _neutral_sentiment(ticker)
        output["sentiment"][ticker] = sig.model_dump()
        data_ages.setdefault(ticker, {})["sentiment_days"] = sentiment_days

    # ── Stage 4: Backtests ────────────────────────────────────────────────────
    log.info("Stage 4: Loading backtest results + MeLLeA interpretation...")
    for ticker in tickers:
        bt_data = load_backtest_json(ticker)
        if bt_data:
            try:
                bt_dt = datetime.fromisoformat(bt_data["date"])
                backtest_days = int((datetime.now() - bt_dt.replace(tzinfo=None)).total_seconds() / 86400)
                signal_dates.setdefault(ticker, {})["backtest_date"] = bt_dt.strftime("%Y-%m-%d")
            except (KeyError, ValueError):
                backtest_days = "no file found"
                signal_dates.setdefault(ticker, {})["backtest_date"] = "unknown"
            # Inject current_price from the forecast signal when the backtest JSON
            # was produced by the older percentage-based script and lacks it.
            # interpret_backtest needs current_price to compute stop_dollar_amount.
            if "current_price" not in bt_data:
                fc_price = output["forecast"].get(ticker, {}).get("current_price")
                if fc_price:
                    bt_data["current_price"] = fc_price
                    log.info(f"  Injected current_price={fc_price:.2f} into {ticker} backtest (field was absent)")
            bs = interpret_backtest(ticker=ticker,
                                    backtest_data=json.dumps(bt_data, indent=2))
            output["backtest"][ticker] = bs.model_dump()
        else:
            backtest_days = "no file found"
            signal_dates.setdefault(ticker, {})["backtest_date"] = "unknown"
        data_ages.setdefault(ticker, {})["backtest_days"] = backtest_days

    # Persist signal freshness dates and data ages into the output JSON
    output["signal_dates"] = signal_dates
    output["data_ages"]    = data_ages

    # ── Stage 5: Daily advisor ────────────────────────────────────────────────
    log.info("Stage 5: MeLLeA daily advisor (majority voting)...")

    # Compute combined scores deterministically before passing to MeLLeA
    combined_scores = compute_combined_scores(output["forecast"], output["sentiment"], tickers)
    log.info(f"  Combined scores: {combined_scores}")

    # Load persisted positions so the advisor knows about existing holdings
    positions = load_positions()
    if positions["open_positions"]:
        portfolio_status = json.dumps(positions, indent=2)
    else:
        portfolio_status = "No existing positions"

    action = daily_advisor(
        portfolio_status   = portfolio_status,
        forecast_decisions = json.dumps({t: output["forecast"].get(t, {})
                                         for t in tickers}, indent=2),
        sentiment_signals  = json.dumps({t: output["sentiment"].get(t, {})
                                         for t in tickers}, indent=2),
        backtest_signals   = json.dumps({t: output["backtest"].get(t, {})
                                         for t in tickers}, indent=2),
        combined_scores    = json.dumps(combined_scores, indent=2),
        cash_available     = BUDGET,
        today_date         = datetime.now().strftime("%Y-%m-%d"),
        data_ages          = json.dumps(data_ages, indent=2),
    )

    output.update({
        "cash_remaining":     action.cash_remaining,
        "tickers_to_buy":     action.tickers_to_buy,
        "tickers_to_sell":    action.tickers_to_sell,
        "tickers_to_hold":    action.tickers_to_hold,
        "tickers_to_monitor": action.tickers_to_monitor,
        "stop_loss_orders":   action.stop_loss_orders,
        "combined_scores":    combined_scores,       # use the deterministic Python scores
        "buy_trigger_prices": action.buy_trigger_prices,
        "user_prompt":        action.user_prompt,
        "actions_by_ticker":  {
            **{t: "buy"     for t in action.tickers_to_buy},
            **{t: "sell"    for t in action.tickers_to_sell},
            **{t: "hold"    for t in action.tickers_to_hold},
            **{t: "monitor" for t in action.tickers_to_monitor},
        },
    })

    # ── Event Calendar Guard ──────────────────────────────────────────────────
    guard = EarningsCalendarGuard()
    event_alerts = guard.get_alerts(action)
    output["event_alerts"] = [a.model_dump() for a in event_alerts]
    output["event_guard_window"] = guard.window_days
    if event_alerts:
        window = guard.window_days
        alert_lines = "\n".join(
            f"  • {a.ticker} [{a.severity.upper()}]: "
            f"{a.event_type.replace('_', ' ')} on {a.event_date} "
            f"({a.days_until_event}d) — {a.recommendation}"
            for a in event_alerts
        )
        output["user_prompt"] = (
            action.user_prompt
            + f"\n\n⚠️ EVENT CALENDAR ALERTS (next {window} days):\n"
            + alert_lines
        )

    # Persist portfolio state for the next run
    save_positions(output)

    return output


# ── Dashboard HTML embedding ──────────────────────────────────────────────────

def embed_data_in_dashboard(pipeline_output: dict) -> None:
    """Re-embed pipeline_output.json and positions.json as inline JS variables
    in pipeline_daily_sheet.html so the dashboard works by opening the file
    directly in a browser without a local server.

    Called automatically at the end of every pipeline run (live and mock),
    so the HTML always reflects the latest results without manual steps.
    """
    html_path = BASE_DIR / "pipeline_daily_sheet.html"
    if not html_path.exists():
        log.warning("pipeline_daily_sheet.html not found — skipping dashboard embed.")
        return

    positions = load_positions()

    pipeline_json  = json.dumps(pipeline_output, default=str)
    positions_json = json.dumps(positions, default=str)

    html = html_path.read_text(encoding="utf-8")

    import re

    # Replace embedded pipeline data
    # Use lambda replacement to prevent re.sub treating \uXXXX in JSON as regex escapes
    _pj = 'var PIPELINE_DATA = ' + pipeline_json + ';'
    html = re.sub(
        r'var PIPELINE_DATA\s*=\s*\{.*?\};',
        lambda _: _pj,
        html, flags=re.DOTALL
    )
    # Replace embedded positions data
    _posj = 'var POSITIONS_DATA = ' + positions_json + ';'
    html = re.sub(
        r'var POSITIONS_DATA\s*=\s*\{.*?\};',
        lambda _: _posj,
        html, flags=re.DOTALL
    )
    # Remove any stale "pipeline re-run required" notice left from a prior partial state
    html = re.sub(
        r'\n// -- Pipeline-pending notice.*?document\.getElementById\(\'warnings\'\)\.prepend\(el\);\s*\}\)\(\);\s*',
        '\n',
        html, flags=re.DOTALL
    )

    html_path.write_text(html, encoding="utf-8")
    log.info(f"Dashboard updated — tickers: {pipeline_output.get('all_tickers', [])}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info(f"=== Daily Pipeline {'(MOCK)' if MOCK_MODE else '(LIVE)'} — "
             f"{datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    output = make_mock_output() if MOCK_MODE else run_live_pipeline()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    embed_data_in_dashboard(output)

    log.info(f"Pipeline complete. Output: {OUTPUT_PATH}")
    print(f"\n[OK] Pipeline output written to: {OUTPUT_PATH}")
    print(f"  Tickers: {output.get('all_tickers', [])}")
    print(f"  Buy:     {output.get('tickers_to_buy', [])}")
    print(f"  Hold:    {output.get('tickers_to_hold', [])}")
    print(f"  Cash:    ${output.get('cash_remaining', 0):.2f}")


if __name__ == "__main__":
    main()

# Made with Bob
