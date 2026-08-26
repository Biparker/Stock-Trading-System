# ETN & CAT — Time Series Analysis Report
**Date:** 2026-06-13  
**Analysis Period:** 2025-06-30 → 2026-06-30 (252 trading days)  
**Forecast Horizon:** 36 business days (2026-07-01 → 2026-08-19)  
**Models Run:** XGBoost · ARIMA · Linear Regression  
**Stop Loss (Updated):** 3% (revised from 2%)

---

## ETN (Eaton Corporation plc)

### Historical Context
| Metric | Value |
|---|---|
| Current Price | $425.27 |
| 1-Year Price Change | +20.51% |
| 1-Year Range | $313.97 – $435.78 |
| Avg Price | $367.05 |
| Daily Volatility | 2.19% |
| Trend Strength (R²) | 0.242 (Moderate) |
| ADF Stationarity | Non-stationary (p=0.483) |

### Model Comparison — ETN

| Model | Day-1 Forecast | Day-36 Forecast | Change vs Now | RMSE | MAE | MAPE | Signal |
|---|---|---|---|---|---|---|---|
| **XGBoost** | $418.72 | $406.61 | **-4.39%** | **1.15** | **0.83** | 0.23% | DOWNTREND |
| **ARIMA** | $421.96 | $420.70 | -1.07% | 23.58 | 7.34 | 2.00% | DOWNTREND |
| **Linear Regression** | $419.34 | $471.20 | +10.80% | 7.67 | 5.66 | 1.53% | UPTREND |

### Interpretation — ETN
- **XGBoost is the most accurate model** (RMSE 1.15 vs 7.67 vs 23.58) — lowest error by a large margin
- XGBoost and ARIMA both signal **DOWNTREND** over the 36-day window; Linear Regression disagrees
- LR extrapolates the moderate uptrend linearly (+10.8%) — likely overfit to the gentle slope
- ARIMA's high RMSE (23.58) and MAPE (2.0%) confirm it struggles with the non-stationary data
- **Consensus lean: DOWNTREND** — 2 of 3 models show a pullback from the recent $435 high
- The +20.5% 1-year gain suggests some near-term consolidation is technically reasonable
- **Stage 1 Decision: FAIL** — XGBoost (most trusted model) forecasts -4.39% decline vs required +5% threshold

---

## CAT (Caterpillar Inc.)

### Historical Context
| Metric | Value |
|---|---|
| Current Price | $1,067.32 |
| 1-Year Price Change | +177.91% |
| 1-Year Range | $384.05 – $1,067.32 |
| Avg Price | $632.93 |
| Daily Volatility | 2.32% |
| Trend Strength (R²) | 0.948 (Very Strong) |
| ADF Stationarity | Non-stationary (p=0.994) |

### Model Comparison — CAT

| Model | Day-1 Forecast | Day-36 Forecast | Change vs Now | RMSE | MAE | MAPE | Signal |
|---|---|---|---|---|---|---|---|
| **XGBoost** | $1,026.98 | $995.15 | **-6.76%** | **2.86** | **1.90** | 0.29% | DOWNTREND |
| **ARIMA** | $1,045.29 | $1,145.11 | +7.29% | 31.26 | 13.60 | 2.29% | UPTREND |
| **Linear Regression** | $1,047.97 | $1,702.48 | +59.51% | 14.53 | 10.47 | 1.56% | UPTREND |

### Interpretation — CAT
- **XGBoost again most accurate** (RMSE 2.86 vs 14.53 vs 31.26)
- Sharp model disagreement: XGBoost sees mean-reversion after the extraordinary +178% 1-year run
- Linear Regression's +59.5% projection is an artifact of extrapolating a parabolic trend — unreliable
- ARIMA's +7.3% is plausible directionally but its RMSE (31.26) and MAPE (2.3%) are the worst
- The ADF p-value of 0.994 (near-random walk) explains ARIMA's poor fit — it was not designed for this regime
- **Stage 1 Decision: FAIL** — XGBoost forecasts -6.76%, well below the +5% threshold; extreme valuation risk

---

## Cross-Model Summary

| Ticker | Best Model | Best RMSE | XGB Signal | ARIMA Signal | LR Signal | Consensus |
|---|---|---|---|---|---|---|
| ETN | XGBoost (1.15) | 1.15 | DOWNTREND (-4.4%) | DOWNTREND (-1.1%) | UPTREND (+10.8%) | **DOWNTREND** |
| CAT | XGBoost (2.86) | 2.86 | DOWNTREND (-6.8%) | UPTREND (+7.3%) | UPTREND (+59.5%) | **MIXED** |

## Why XGBoost Wins on Accuracy
- Both stocks are **non-stationary** — ARIMA requires differencing and loses accuracy rapidly
- The MACD features + lag windows in XGBoost capture regime changes that linear models miss
- CAT's parabolic trend makes LR completely unreliable; XGB adapts via tree splits on recent price levels
- MAPE for XGBoost: ETN 0.23%, CAT 0.29% — both under 0.3% vs 1.5–2.3% for the other models

## Stage 1 Outcome
Both ETN and CAT **fail Stage 1** on the XGBoost primary model (require +5% 36-day forecast):
- ETN: -4.39% (XGB) — pullback after $435 recent high; consolidation expected
- CAT: -6.76% (XGB) — mean-reversion signal after extraordinary +178% 1-year run

Neither advances to backtesting at this time. Revisit after next earnings cycle.
