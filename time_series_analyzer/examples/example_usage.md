# Time-Series Analysis Tool - Usage Examples

## Quick Start

### 1. Basic Usage - Auto Method Selection

```bash
cd time_series_analyzer
python main.py --ticker AAPL
```

This will:
- Fetch 1 year of Apple stock data
- Analyze data characteristics
- Recommend best forecasting method
- Generate forecast with 95% confidence intervals
- Create visualizations and reports

### 2. Specify Forecasting Method

```bash
# Use Prophet method
python main.py --ticker MSFT --method prophet

# Use LSTM neural network
python main.py --ticker GOOGL --method lstm

# Use ARIMA method
python main.py --ticker TSLA --method arima
```

### 3. Select Specific Features

```bash
# Analyze using only close price and volume
python main.py --ticker AAPL --features close volume

# Include all available features
python main.py --ticker AAPL --features close open high low volume
```

### 4. Custom Date Range

```bash
# Analyze specific period
python main.py --ticker AAPL \
  --start-date 2023-06-01 \
  --end-date 2024-06-01
```

### 5. Interactive Mode

```bash
# Use interactive prompts for all selections
python main.py --ticker AAPL --interactive
```

### 6. Complete Example

```bash
python main.py \
  --ticker AAPL \
  --method prophet \
  --features close volume \
  --start-date 2023-01-01 \
  --end-date 2024-01-01
```

## Available Methods

| Method | Best For | Speed | Data Required |
|--------|----------|-------|----------------|
| linear_regression | Strong trends | Very Fast | > 50 points |
| arima | Stationary data | Fast | > 50 points |
| exponential_smoothing | Trend + seasonality | Fast | > 100 points |
| prophet | Non-stationary, seasonal | Medium | > 100 points |
| lstm | Complex patterns | Slow | > 250 points |
| xgboost | Mixed patterns | Medium | > 100 points |

## Available Stock Tickers

US Market Examples:
- **Tech**: AAPL, MSFT, GOOGL, TSLA, NVIDIA (NVDA), META
- **Finance**: JPM, BAC, GS, BLK
- **Healthcare**: JNJ, PFE, MRNA, UNH
- **Energy**: XOM, CVX
- **Retail**: AMZN, WMT, TGT

## Output Files

After running analysis, check these directories:

```
time_series_analyzer/
├── output/
│   ├── plots/
│   │   ├── {TICKER}_historical.png
│   │   ├── {TICKER}_forecast_{METHOD}.png
│   │   └── {TICKER}_decomposition.png
│   ├── {TICKER}_forecast_report.txt
│   └── {TICKER}_forecast_report.json
```

## Understanding the Report

### Data Summary
Shows historical price patterns:
- Price range (min, max, average)
- Volatility (price change)
- Overall trend

### Data Characteristics Analysis
Explains what patterns were detected:
- **Stationarity**: Is the data mean-reverting or trending?
- **Trend**: Is there a clear uptrend or downtrend?
- **Seasonality**: Are there regular patterns (weekly, monthly)?
- **Volatility**: How much does the price fluctuate?

### Selected Method Explanation
Why this method was chosen for your data.

### Forecast Results
The actual predictions with:
- **Date**: Forecasted date
- **Forecast**: Expected price
- **Lower Bound**: 95% confidence interval lower bound
- **Upper Bound**: 95% confidence interval upper bound
- **Range**: Uncertainty range

### Model Metrics
Performance measures on historical data:
- **RMSE**: Root Mean Squared Error (lower is better)
- **MAE**: Mean Absolute Error
- **MAPE**: Mean Absolute Percentage Error

### Risk Assessment
- Confidence interval widths (narrower = more confident)
- Data-specific warnings (high volatility, limited data, etc.)

## Example Output Interpretation

```
FORECAST RESULTS (95% Confidence Interval)

Date       Forecast    Lower Bound Upper Bound Range
2024-01-15 $185.50     $182.30     $188.70     $6.40
2024-01-16 $186.20     $181.95     $190.45     $8.50
2024-01-17 $186.80     $181.60     $192.00     $10.40
```

This means:
- On Jan 15, we expect AAPL at ~$185.50
- We're 95% confident it will be between $182.30 and $188.70
- Uncertainty increases over time (wider ranges)

## Troubleshooting

### "No data found for ticker"
- Check ticker symbol spelling (case insensitive, AAPL = aapl)
- Verify stock is actively traded
- Try a different ticker

### "LSTM training failed"
- Use a ticker with more historical data
- Try a simpler method (prophet, arima)
- Reduce lookback period in config.py

### "Forecast looks unrealistic"
- This is normal for volatile stocks
- Check confidence intervals (wide = uncertain)
- Consider using different method
- Look at recent trends in the data plot

### Memory issues
- Close other applications
- Use a simpler method
- Reduce historical data period
- Check your system RAM

## Best Practices

1. **Start with auto-selection**: Let the agent recommend the method
2. **Review the data summary**: Understand historical patterns
3. **Check the analysis report**: See what was detected
4. **Look at the forecast plot**: Visualize the prediction
5. **Read confidence intervals**: Understand the uncertainty
6. **Consider recent context**: Did something change recently?

## Advanced Usage

### Python API

```python
from src.main_analyzer import TimeSeriesAnalyzer

analyzer = TimeSeriesAnalyzer('AAPL')
result = analyzer.run_analysis(method='prophet', features=['close'])

forecast = result['forecast']['forecast']
confidence_lower = result['forecast']['confidence_interval']['lower']
confidence_upper = result['forecast']['confidence_interval']['upper']
```

### Using Individual Components

```python
from src.data_fetcher import DataFetcherAgent
from src.method_recommender import MethodRecommenderAgent
from src.forecasting_methods import get_forecaster

# Fetch data
fetcher = DataFetcherAgent()
result = fetcher.fetch_stock_data('AAPL')
data = result['data']

# Get recommendations
recommender = MethodRecommenderAgent(data)
recommendations = recommender.recommend_methods()

# Use specific method
forecaster = get_forecaster('prophet', data)
forecaster.fit()
forecaster.predict()
forecast = forecaster.get_forecast()
```

## Important Reminders

⚠️ **Not Financial Advice**: This tool is for educational analysis only.

- Use predictions as one input among many
- Consider fundamental analysis
- Check recent news and events
- Consult financial advisors
- Never invest based solely on technical forecast
- Past performance ≠ future results

## Need Help?

1. Check the README.md for detailed documentation
2. Review example scripts in examples/
3. Run tests: `pytest tests/ -v`
4. Check sample outputs in output/
5. Review the configuration in src/config.py

Enjoy analyzing stock prices! 📈
