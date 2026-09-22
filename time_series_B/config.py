"""Configuration for Time Series B -- XGBoost 30-day relative return forecaster.

Key design differences from time_series_analyzer (Method A):
  - 3 years of data: year 1-2 = training, year 3 = out-of-sample validation
  - Target: 30-day FORWARD RELATIVE RETURN (%), not absolute price
  - Direct multi-output prediction (no iterative chaining -> no error compounding)
  - Richer feature set: lag returns, MACD, RSI, Bollinger Bands, volume ratio
"""

import os

# ── Data ─────────────────────────────────────────────────────────────────────
LOOKBACK_YEARS      = 3          # Total history to fetch (calendar years)
TRAIN_YEARS         = 2          # First N years used for training
FORECAST_DAYS       = 30         # Trading-day horizon for relative return target

# ── Feature Engineering ───────────────────────────────────────────────────────
LAG_DAYS            = [1, 2, 3, 5, 10, 20, 30]   # Return lag periods (trading days)
RSI_PERIOD          = 14
MACD_FAST           = 12
MACD_SLOW           = 26
MACD_SIGNAL         = 9
BB_PERIOD           = 20
BB_STD              = 2.0
VOL_MA_PERIOD       = 20         # Volume moving-average denominator

# ── XGBoost ───────────────────────────────────────────────────────────────────
# Best validated config (MU test: Val Dir-Acc 92.1%, RMSE 36.0):
#   max_depth=3 + min_child_weight=10 produces a highly regularised model
#   that generalises well on year-3 out-of-sample data.
XGB_N_ESTIMATORS     = 10      # small fixed count -- model converges fast at this regularisation
XGB_LEARNING_RATE    = 0.05
XGB_MAX_DEPTH        = 3       # shallow trees
XGB_SUBSAMPLE        = 0.8
XGB_COLSAMPLE        = 0.8
XGB_MIN_CHILD_WEIGHT = 10      # strong leaf regularisation -- best val accuracy
XGB_RANDOM_STATE     = 42

# ── Acceptance threshold (Stage 1 gate) ───────────────────────────────────────
MIN_FORECAST_RETURN = 5.0        # % -- stock must be forecast to return >= this

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE       = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(_HERE, 'output')
PLOTS_DIR   = os.path.join(OUTPUT_DIR, 'plots')
