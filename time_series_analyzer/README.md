# Time-Series Stock Price Forecasting Tool

A comprehensive Python tool for analyzing stock price time-series data and generating short-term price predictions using multiple forecasting methods with intelligent method recommendation.

## Features

### 🤖 Intelligent Agent System
- **Data Fetcher Agent**: Automatically downloads 1 year of historical stock data using yfinance
- **Method Recommender Agent**: Analyzes data characteristics (stationarity, trend, seasonality, volatility) and recommends the best 2-3 forecasting methods with detailed reasoning
- **Multi-method Comparison**: Support for 6 different forecasting approaches

### 📊 Forecasting Methods
1. **Linear Regression** - Simple trend-based baseline
2. **ARIMA** - Classical statistical time-series model with auto parameter selection
3. **Exponential Smoothing** - Triple exponential smoothing (Holt-Winters) for trend + seasonality
4. **Prophet** - Meta's robust forecasting tool with seasonality handling
5. **LSTM** - Deep learning neural network for complex patterns
6. **XGBoost** - Gradient boosting machine learning model

### 📈 Analysis & Output
- **95% Confidence Intervals** on all forecasts
- **Professional Visualizations**:
  - Historical price trends
  - Forecast with confidence bands
  - Seasonal decomposition
  - Multi-method comparison charts
  - Model performance metrics comparison
- **Detailed Reports**:
  - Text report with analysis summary
  - JSON report for programmatic access
  - Data characteristics analysis
  - Risk assessment and disclaimers

### 🎯 User Features
- **Interactive Feature Selection**: Choose which price metrics to include (open, high, low, close, volume)
- **Automatic or Manual Method Selection**: Let the agent recommend or specify your preferred method
- **Flexible Data Input**: Custom date ranges for analysis
- **Clear Data Summary**: Overview of historical data patterns

## Installation

### Prerequisites
- Python 3.8 or higher
- pip or conda package manager

### Setup

1. Navigate to the time_series_analyzer directory:
```bash
cd time_series_analyzer
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

This will install all required packages:
- yfinance (stock data)
- pandas, numpy (data processing)
- scikit-learn (ML models)
- statsmodels (ARIMA, ETS, statistical tests)
- prophet (Meta's forecasting)
- xgboost (gradient boosting)
- tensorflow (LSTM neural network)
- matplotlib, seaborn, plotly (visualization)
- scipy (statistical functions)

## Usage

### Interactive Mode
```bash
python main.py
```
The tool will prompt you for:
1. Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)
2. Feature selection (which price metrics to analyze)
3. Forecasting method (or auto-select)

### Command Line Mode

**Basic usage with auto method selection:**
```bash
python main.py --ticker AAPL
```

**Specify forecasting method:**
```bash
python main.py --ticker AAPL --method prophet
```

**Select specific features:**
```bash
python main.py --ticker MSFT --features close volume open
```

**Custom date range:**
```bash
python main.py --ticker GOOGL --start-date 2023-01-01 --end-date 2024-01-01
```

**Interactive feature selection:**
```bash
python main.py --ticker AAPL --interactive
```

### Available Forecasting Methods
- `auto` - Automatic selection based on data characteristics (default)
- `linear_regression` - Linear trend forecasting
- `arima` - Auto ARIMA with parameter selection
- `exponential_smoothing` - Holt-Winters smoothing
- `prophet` - Meta's Prophet model
- `lstm` - LSTM neural network
- `xgboost` - XGBoost gradient boosting

## Output

The tool generates outputs in the following locations:

### Plots Directory (`output/plots/`)
- `{TICKER}_historical.png` - Historical price data
- `{TICKER}_forecast_{METHOD}.png` - Forecast with 95% confidence intervals
- `{TICKER}_decomposition.png` - Seasonal decomposition analysis

### Reports Directory (`output/`)
- `{TICKER}_forecast_report.txt` - Detailed text report with all findings
- `{TICKER}_forecast_report.json` - Machine-readable JSON report

## Data Characteristics Analysis

The recommender agent analyzes:

### Stationarity (ADF Test)
- **Stationary**: No differencing needed, suitable for ARIMA
- **Non-stationary**: Requires differencing, Prophet/Linear Regression recommended

### Trend Analysis
- **Strong Trend**: Prophet, Linear Regression, ETS recommended
- **Weak Trend**: ARIMA, LSTM suitable
- Measures R-squared of linear trend fit

### Seasonality Detection
- **Strong Seasonality**: Prophet, ETS, LSTM recommended
- **Weak/No Seasonality**: Linear Regression, ARIMA suitable
- Uses seasonal decomposition with 252-day periods

### Volatility Analysis
- **High Volatility**: LSTM, XGBoost recommended (complex pattern capture)
- **Low Volatility**: All methods viable
- Measures coefficient of variation of returns

### Data Length Evaluation
- **< 100 records**: Simple methods (Linear Regression, ETS) recommended
- **100-250 records**: ARIMA, Prophet viable
- **> 250 records**: All methods viable

## Forecast Output

Each forecast includes:
- **Point Predictions**: Expected price for each forecasted day
- **95% Confidence Interval**: Lower and upper bounds capturing uncertainty
- **Model Metrics**: RMSE, MAE, MAPE (Mean Absolute Percentage Error)
- **Summary Statistics**: Mean, min, max of forecasted values
- **Risk Assessment**: Confidence interval widths and volatility warnings

## Example Report Structure

```
EXECUTIVE SUMMARY
- Stock ticker and company name
- Analysis and forecast periods
- Current price and historical metrics

DATA SUMMARY
- Price range statistics
- Volatility metrics
- Price change percentage

DATA CHARACTERISTICS ANALYSIS
- Stationarity test results
- Trend analysis (direction and strength)
- Seasonality detection
- Volatility level assessment

SELECTED FORECASTING METHOD
- Method name and rationale

FORECAST RESULTS
- Detailed forecast table with confidence intervals
- Summary statistics
- Model performance metrics

RISK ASSESSMENT
- Confidence interval widths
- Key risk factors and warnings

DISCLAIMERS
- Important investment risk warnings
```

## Advanced Usage

### Programmatic Access

```python
from src.main_analyzer import TimeSeriesAnalyzer

# Create analyzer instance
analyzer = TimeSeriesAnalyzer('AAPL', interactive=False)

# Run analysis
result = analyzer.run_analysis(method='prophet', features=['close', 'volume'])

# Access results
forecast = result['forecast']['forecast']
confidence_intervals = result['forecast']['confidence_interval']
analysis_data = result['analysis']
```

### Individual Component Usage

```python
from src.data_fetcher import DataFetcherAgent
from src.method_recommender import MethodRecommenderAgent
from src.forecasting_methods import get_forecaster

# Fetch data
fetcher = DataFetcherAgent()
result = fetcher.fetch_stock_data('AAPL')
data = result['data']

# Analyze data
recommender = MethodRecommenderAgent(data)
recommender.print_analysis_report()

# Get specific forecaster
forecaster = get_forecaster('prophet', data, feature_col='close')
forecaster.fit()
forecaster.predict()
forecast = forecaster.get_forecast()
```

## Configuration

Edit `src/config.py` to adjust:
- `LOOKBACK_DAYS` (365): Historical data window
- `FORECAST_DAYS`: Forecast horizon (default: 10% of lookback)
- `CONFIDENCE_LEVEL` (0.95): Confidence interval level
- ARIMA parameters (max p, d, q values)
- LSTM/XGBoost hyperparameters
- Visualization settings
- Statistical test thresholds

## Testing

Run the test suite:
```bash
pytest tests/
```

Run specific test:
```bash
pytest tests/test_data_fetcher.py -v
```

## Limitations

- **Short-term forecasts only**: 1 month predictions (~10% of historical data)
- **Past patterns assumption**: Uses historical patterns which may not continue
- **Unexpected events**: Cannot account for sudden market disruptions
- **Single-feature focus**: Close price is the primary target variable
- **Business days only**: Uses 252 trading days per year for frequency

## Important Disclaimers

⚠️ **This tool is for educational and research purposes only.**

- Stock prices are influenced by numerous factors not captured in historical data
- Market conditions and unexpected events can cause significant deviations
- Do not use this forecast as the sole basis for investment decisions
- Past performance does not guarantee future results
- Consult with a financial advisor before making investment decisions
- The authors assume no liability for any financial losses

## Project Structure

```
time_series_analyzer/
├── src/
│   ├── __init__.py
│   ├── config.py                    # Configuration constants
│   ├── data_fetcher.py              # Stock data fetching agent
│   ├── feature_selector.py          # Feature selection interface
│   ├── forecasting_methods.py       # All forecasting implementations
│   ├── method_recommender.py        # Analysis & recommendation agent
│   ├── visualizer.py                # Plotting and visualization
│   ├── report_generator.py          # Report generation
│   └── main_analyzer.py             # Main orchestrator
├── tests/
│   ├── __init__.py
│   ├── test_data_fetcher.py
│   ├── test_forecasters.py
│   └── test_recommender.py
├── data/                            # Sample data directory
├── output/                          # Generated reports and plots
├── examples/                        # Example scripts
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Performance Notes

### Typical Execution Times
- **Data Fetching**: 2-5 seconds
- **Linear Regression**: < 1 second
- **ARIMA**: 5-15 seconds
- **Exponential Smoothing**: 2-5 seconds
- **Prophet**: 10-30 seconds
- **LSTM**: 30-120 seconds (depends on data size)
- **XGBoost**: 5-15 seconds
- **Total with all visualizations**: 1-3 minutes

### Memory Requirements
- **Typical usage**: 500 MB - 2 GB
- **LSTM with large data**: Up to 4 GB

## Troubleshooting

### Common Issues

**"No data found for ticker"**
- Verify the ticker symbol is correct
- Check if the stock is still actively traded
- Try a different ticker

**"Insufficient data for LSTM training"**
- LSTM requires more historical data
- Use a ticker with longer history
- Try a different forecasting method

**Memory errors**
- Reduce lookback period in config.py
- Close other applications
- Use a simpler method (Linear Regression, ARIMA)

**Import errors**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify virtual environment is activated
- Check Python version is 3.8+

## Contributing

To add new forecasting methods:
1. Create a new class inheriting from `ForecastingBase`
2. Implement `fit()` and `predict()` methods
3. Add to `get_forecaster()` factory function
4. Update method recommender logic if needed
5. Add tests in `tests/` directory

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Check the troubleshooting section above
- Review example outputs in `examples/` directory
- Examine test files for usage examples
- Submit issues with stock ticker and method used

## Version History

### v1.0.0 (Initial Release)
- 6 forecasting methods (Linear Regression, ARIMA, ETS, Prophet, LSTM, XGBoost)
- Intelligent method recommender agent
- Data fetcher agent with yfinance integration
- Interactive and CLI interfaces
- Comprehensive visualization suite
- Detailed reporting (text and JSON)
- Data characteristic analysis
- 95% confidence intervals

---

**Developed as an educational tool for time-series forecasting analysis.**
