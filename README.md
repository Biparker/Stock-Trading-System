# Stock Trading System

This folder contains the automated stock trading system project, including time series analysis, backtesting, and trading strategy development.

## Project Components

### Time Series Analyzer (`time_series_analyzer/`)
A comprehensive Python tool for analyzing stock price time-series data and generating short-term price predictions using multiple forecasting methods with intelligent method recommendation.

**Features:**
- Intelligent agent system for data fetching and method recommendation
- 6 different forecasting methods (Linear Regression, ARIMA, Exponential Smoothing, Prophet, LSTM, XGBoost)
- Automated analysis and visualization

See `time_series_analyzer/README.md` for detailed documentation.

### Trading Strategy Analysis
- **TRADING_SYSTEM_PLAN.md** - Comprehensive plan for the automated trading system
- **90_DAY_TESTING_STATISTICAL_ANALYSIS.md** - Statistical analysis of 90-day testing period
- **ANNUALIZED_PERCENTILE_ANALYSIS.md** - Percentile-based performance analysis
- **OPTIONS_TRADING_ANALYSIS.md** - Options trading strategy analysis
- **ETF_ALLOCATION_ANALYSIS.md** - ETF integration and optimal allocation strategy (NEW)
- **WEEKLY_STOP_LOSS_ANALYSIS.md** - Weekly stop-loss strategy analysis

### Backtesting Tools
- **weekly_stop_loss_backtest.py** - Backtesting script for weekly stop-loss strategies
- **weekly_stop_loss_results.json** - Results from backtesting
- **weekly_stop_loss_comparison.png** - Visual comparison of strategies

## Getting Started

1. Navigate to the `time_series_analyzer/` directory for the core forecasting tool
2. Review `TRADING_SYSTEM_PLAN.md` for the overall system architecture
3. Examine the analysis documents for strategy insights

## Organization

**B. I. Parker Data Science and Consulting LLC**

This project is developed for both internal trading operations and as a commercial product offering.