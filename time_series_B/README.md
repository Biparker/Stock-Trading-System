# Time Series B — XGBoost 30-Day Relative Return Forecaster

**Status: ACTIVE** (Method A / `time_series_analyzer` is kept intact but inactive for Stage 1 screening)

## Key Design Differences vs Method A

| | Method A (`time_series_analyzer`) | Method B (`time_series_B`) |
|---|---|---|
| **Data** | 1 year | **3 years** |
| **Train/Val split** | None (full history used) | **Years 1-2 train, Year 3 out-of-sample validation** |
| **Target** | Absolute price in 36 days | **30-day forward relative return (%)** |
| **Prediction method** | Iterative chaining (error compounds) | **Direct single-shot** (no compounding) |
| **Features** | Close price lags + MACD | **Return lags + RSI + MACD + Bollinger Bands + Volume ratio + ATR** |
| **Stage 1 pass** | Forecast price > current + 5% | **Forecast return ≥ +5%** |

## Why Relative Return?

Predicting **returns** rather than **prices**:
- Removes price-level non-stationarity — the model learns patterns, not magnitudes
- Directly answers the Stage 1 question: "does this stock have enough upside?"
- Return distributions are more stable across time and across stocks
- No iterative error compounding — one clean prediction per stock

## Usage

```bash
# From stock-trading-system/time_series_B/ directory
python main.py --ticker AAPL
python main.py --ticker MSFT --threshold 3.0    # override +5% threshold
python main.py --ticker GOOGL --no-plots
```

## Output Files (saved to `time_series_B/output/`)

| File | Contents |
|---|---|
| `TICKER_tsB_report.json` | Full structured report: metadata, model metrics, feature importance, prediction |
| `TICKER_tsB_report.txt` | Human-readable text summary |
| `plots/TICKER_tsB_forecast.png` | 2-panel chart: price history + validation residual distribution |

## Module Structure

```
time_series_B/
  main.py              ← Entry point
  config.py            ← All parameters (data window, XGBoost, threshold)
  data_fetcher.py      ← 3-year yfinance fetch
  feature_engineer.py  ← All feature and target construction
  xgboost_model.py     ← Train/val split, XGBoost fit, direct prediction
  report_generator.py  ← JSON + text report generation
  visualizer.py        ← 2-panel matplotlib chart
  output/              ← Reports and plots (auto-created)
```

## Stage 1 Integration

The exit code indicates pass/fail for scripting:
- Exit code `0` = PASS (forecast return ≥ threshold)
- Exit code `1` = FAIL

The `output/TICKER_tsB_report.json` field `prediction.signal` = `"PASS"` or `"FAIL"`.
