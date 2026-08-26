# Stock Trading System — MeLLeA Enhanced

**B. I. Parker Data Science and Consulting LLC**

An automated S&P 500 stock trading system with a 5-stage MeLLeA-powered analysis pipeline and an interactive Streamlit dashboard. The system selects equities from the Financial, Technology, and Healthcare sectors within a $2,500 portfolio budget, analyses them using XGBoost forecasting, FinBERT sentiment analysis, and 3-year Monte Carlo backtesting, then delivers daily structured trading advice via IBM MeLLeA.

---

## Architecture Overview

```
Stage 0  Screen S&P500 candidates (generate_candidates.py)
Stage 1  MeLLeA select_candidates()   → CandidateList schema
Stage 2  XGBoost 30-day forecast      → ForecastDecision schema
Stage 3  FinBERT sentiment analysis   → SentimentSignal schema
Stage 4  ATR backtest results         → BacktestSignal schema
Stage 5  MeLLeA daily_advisor()       → DailyAction schema
                    ↓
         Streamlit Dashboard  →  http://localhost:8501
                    ↓
         Railway Pro  →  https://your-app.railway.app
```

---

## Project Structure

```
stock-trading-system/
│
├── mellea_schemas.py          # Pydantic output schemas for all MeLLeA functions
├── mellea_agents.py           # @mellea.function decorated LLM agent functions
├── daily_pipeline.py          # Full 5-stage pipeline orchestrator
├── generate_candidates.py     # S&P500 candidate screening and ranking
├── stage2_backtest.py         # 3-year ATR Monte Carlo backtest engine
├── run_local.py               # Single-command localhost launcher
│
├── dashboard/
│   ├── app.py                 # Streamlit interactive dashboard
│   ├── data_loader.py         # Pipeline JSON + forecast/backtest file loader
│   ├── charts.py              # Plotly chart builders
│   └── requirements.txt       # Dashboard-only dependencies
│
├── time_series_analyzer/      # XGBoost / ARIMA / Prophet forecasting engine
│   └── src/
│       ├── main_analyzer.py   # TimeSeriesAnalyzer orchestrator
│       ├── forecasting_methods.py
│       └── data_fetcher.py
│
├── sentiment_analyzer/        # FinBERT NLP sentiment engine
│   ├── main.py
│   ├── src/
│   │   ├── sentiment_engine.py
│   │   ├── pdf_extractor.py
│   │   └── trading_integrator.py
│   └── Analyst_reports/       # Place downloaded Merrill Lynch PDFs here
│
├── Analysis_Outcomes/         # Pre-computed backtest JSON results
│   ├── AMGN_stage2_backtest.json
│   ├── JNJ_stage2_backtest.json
│   ├── MU_stage2_backtest.json
│   ├── META_stage2_backtest.json
│   └── C_stage2_backtest.json
│
├── forecasts/                 # Pre-computed XGBoost forecast JSON results
├── data/                      # Pipeline runtime output (pipeline_output.json)
│
├── requirements.txt           # Full project dependencies
├── railway.toml               # Railway dashboard deployment config
├── railway.cron.toml          # Railway daily pipeline cron config
└── .env.example               # Environment variable template
```

---

## Quick Start — Localhost

### Prerequisites

- Python 3.10 or newer
- Anaconda or standard Python installation

### 1. Install dependencies

```powershell
cd stock-trading-system
pip install -r requirements.txt
```

### 2. Generate mock pipeline data (no API key needed)

```powershell
python daily_pipeline.py --mock
```

Output: `data/pipeline_output.json`

Expected output:
```
[OK] Pipeline output written to: data\pipeline_output.json
  Tickers: ['AMGN', 'JNJ', 'MU', 'META', 'C']
  Buy:     ['AMGN']
  Hold:    ['JNJ', 'MU']
  Cash:    $625.00
```

### 3. Launch the dashboard

```powershell
python -m streamlit run dashboard/app.py
```

Open **http://localhost:8501** in your browser.

> **Note:** Step 2 only needs to run once. After that, only Step 3 is needed
> to start the dashboard. Re-run Step 2 any time you want fresh pipeline data.

### 4. One-command launcher (alternative)

```powershell
python run_local.py
```

This runs both steps automatically and opens Streamlit.

---

## Live Pipeline (Requires API Key)

### Configure environment

Copy `.env.example` to `.env` and add your API key:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```
# Choose one backend:

# Option A — OpenAI
MELLEA_BACKEND=openai
MELLEA_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_api_key_here

# Option B — IBM Granite
MELLEA_BACKEND=granite
MELLEA_MODEL=ibm/granite-13b-instruct-v2
IBM_API_KEY=your_ibm_api_key_here

# Option C — Ollama (fully local, no key needed)
MELLEA_BACKEND=ollama
MELLEA_MODEL=llama3.1
```

### Run live pipeline

```powershell
python daily_pipeline.py
```

This performs all 5 stages using live MeLLeA LLM calls and writes fresh
`data/pipeline_output.json`. The dashboard refreshes automatically when
you click **Refresh Data** in the sidebar.

---

## Running a Backtest for a New Ticker

```powershell
python stage2_backtest.py --ticker AAPL
python stage2_backtest.py --ticker NVDA --capital 500
```

Results are saved to `Analysis_Outcomes/{TICKER}_stage2_backtest.json`
and automatically picked up by the pipeline on next run.

---

## Adding a New Analyst Report (Sentiment Analysis)

1. Download the Morningstar/analyst PDF from Merrill Lynch
2. Save it to: `sentiment_analyzer/Analyst_reports/Analyst_{TICKER}.pdf`
3. Re-run the pipeline:
   ```powershell
   python daily_pipeline.py
   ```

---

## Deployment — Railway Pro

### Prerequisites
- GitHub account with this repo pushed
- Railway Pro account at railway.app

### Step 1 — Push to GitHub

```powershell
git remote add origin https://github.com/YOUR_USERNAME/stock-trading-system.git
git push -u origin master
```

### Step 2 — Deploy Dashboard Service

1. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**
2. Select `stock-trading-system`
3. Railway auto-detects `railway.toml` and deploys the Streamlit dashboard
4. Add environment variables in Railway dashboard:
   - `MELLEA_BACKEND`
   - `MELLEA_MODEL`
   - `OPENAI_API_KEY` or `IBM_API_KEY`

Dashboard available at: `https://your-app.railway.app`

### Step 3 — Deploy Cron Job Service (Daily Pipeline)

1. In Railway: **New Service → Empty Service**
2. Connect to same GitHub repo
3. In service settings, set start command:
   ```
   python daily_pipeline.py --output data/pipeline_output.json
   ```
4. Set cron schedule: `0 11 * * 1-5` (7:00 AM EST, Mon–Fri)
5. Add same environment variables as Step 2

Every weekday morning the pipeline runs automatically, writes fresh data,
and the dashboard serves updated results when the user opens it.

---

## Key Constraints (Rev-Plan)

| Constraint | Value |
|---|---|
| Portfolio budget | $2,500 total |
| Sectors | S&P 500 — Financial, Technology, Healthcare |
| Forecast horizon | 30 days (XGBoost) |
| Backtest period | 3 years |
| Acceptance criteria | Sharpe > 0.3 AND P(Loss > 5%) < 5% |
| Stop-loss method | ATR-based trailing stop |
| Budget IVR rule | MeLLeA enforces $2,500 cap at generation time |

---

## MeLLeA Integration Summary

MeLLeA (IBM Research) wraps each analysis stage as a typed Python function.
Every LLM call is guaranteed to return a valid Pydantic object — no raw text,
no malformed JSON. Business rules are enforced via IVR (Instruct-Validate-Repair)
loops that automatically correct any model output violating a constraint.

| Agent Function | Schema | IVR Rules |
|---|---|---|
| `select_candidates()` | `CandidateList` | Total budget <= $2,500 |
| `interpret_forecast()` | `ForecastDecision` | Trend must match predicted return |
| `interpret_sentiment()` | `SentimentSignal` | Score < 40 forces exclude |
| `interpret_backtest()` | `BacktestSignal` | pass/fail must match Sharpe + P(Loss) |
| `daily_advisor()` | `DailyAction` | Never buy a Stage 2 fail; stop orders required for all held positions |

---

## Troubleshooting

### ImportError: numpy._core.multiarray failed to import

NumPy/Pandas version conflict between Anaconda and user-level installs. Fix:

```powershell
pip install "pandas>=2.2.0" --user --upgrade
pip install "numpy>=1.26.4,<2.0" --user --force-reinstall
```

### Dashboard shows "No pipeline data yet"

Run the mock pipeline first:

```powershell
python daily_pipeline.py --mock
```

### MeLLeA import fails

Either install MeLLeA (`pip install mellea`) or use mock mode:

```powershell
python daily_pipeline.py --mock
```

---

## Disclaimer

This system is for informational purposes only and does not constitute
financial advice. All analysis is based on historical data and quantitative
models. Past performance does not guarantee future results. Always conduct
your own due diligence and consult a licensed financial advisor before making
investment decisions. B. I. Parker Data Science and Consulting LLC assumes
no liability for financial losses.

---

*Made with IBM Bob*
