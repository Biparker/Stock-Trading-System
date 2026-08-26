"""Configuration constants for time-series stock analysis tool."""

import os
from datetime import datetime, timedelta

# Data Configuration
LOOKBACK_DAYS = 365
FORECAST_DAYS = int(LOOKBACK_DAYS * 0.1)  # 10% of historical data (~36 days)
CONFIDENCE_LEVEL = 0.95

# Default data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
PLOTS_DIR = os.path.join(OUTPUT_DIR, 'plots')

# Statistical thresholds
ADF_TEST_SIGNIFICANCE = 0.05
SEASONALITY_THRESHOLD = 0.3  # Seasonal component strength
VOLATILITY_HIGH_THRESHOLD = 0.04  # Coefficient of variation
VOLATILITY_LOW_THRESHOLD = 0.01

# ARIMA parameters
ARIMA_MAX_P = 5
ARIMA_MAX_D = 2
ARIMA_MAX_Q = 5
ARIMA_SEASONAL_P = 2
ARIMA_SEASONAL_D = 1
ARIMA_SEASONAL_Q = 2

# Exponential Smoothing parameters
ETS_SEASONAL_PERIODS = 252  # Business days in a year

# Prophet parameters
PROPHET_YEARLY_SEASONALITY = True
PROPHET_WEEKLY_SEASONALITY = True
PROPHET_DAILY_SEASONALITY = False
PROPHET_INTERVAL_WIDTH = 0.95

# LSTM parameters
LSTM_LOOKBACK = 30
LSTM_EPOCHS = 100
LSTM_BATCH_SIZE = 16
LSTM_VALIDATION_SPLIT = 0.2

# XGBoost parameters
XGBOOST_LAG_FEATURES = 30
XGBOOST_LEARNING_RATE = 0.05
XGBOOST_N_ESTIMATORS = 100
XGBOOST_MAX_DEPTH = 5

# Linear Regression parameters
LINEAR_REG_LAG = 30

# Model evaluation metrics
TRAIN_TEST_SPLIT = 0.8

# Feature names
AVAILABLE_FEATURES = {
    'close': 'Close Price (Target)',
    'open': 'Opening Price',
    'high': 'High Price',
    'low': 'Low Price',
    'volume': 'Trading Volume',
    'price_range': 'Price Range (High - Low)',
    'price_change_pct': 'Daily Price Change %',
    'volume_ma': 'Volume Moving Average (20-day)',
}

# Visualization
PLOT_FIGSIZE = (14, 6)
PLOT_DPI = 100
PLOT_STYLE = 'seaborn-v0_8-darkgrid'
PLOT_CONFIDENCE_ALPHA = 0.2

# Report
REPORT_FORMATS = ['text', 'json']
