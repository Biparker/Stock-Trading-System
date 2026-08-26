# Quick Start Guide - Time-Series Stock Price Forecasting Tool

## 🚀 Installation (5 minutes)

### If You Have Multiple Python Installations

Use **Anaconda** (recommended) or **Python 3.11**:

```bash
cd time_series_analyzer

# Option 1: Anaconda (if installed)
/c/Users/bobby/anaconda3/python.exe -m venv venv
source venv/bin/activate

# Option 2: Standard Python 3.11
/c/Users/bobby/AppData/Local/Programs/Python/Python311/python.exe -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Or Use Command Prompt (Easier on Windows)

```cmd
cd C:\Users\bobby\OneDrive\Desktop\Prob-solve26\time_series_analyzer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## ⚡ First Run (3 minutes)

```bash
# Run with default settings (NVIDIA stock, auto method selection)
python main.py --ticker NVDA
```

This will:
1. ✓ Download 1 year of NVIDIA stock data
2. ✓ Analyze data characteristics (stationarity, trend, seasonality, volatility)
3. ✓ Recommend best forecasting method
4. ✓ Generate 1-month forecast with 95% confidence intervals
5. ✓ Create visualizations (historical, forecast, decomposition)
6. ✓ Generate detailed reports (text and JSON)

## 📊 Common Commands

### Method 1: Auto-Select (Recommended for First-Time)
```bash
python main.py --ticker MSFT
```
Agent analyzes data and recommends the best method.

### Method 2: Specify Method
```bash
python main.py --ticker GOOGL --method prophet
python main.py --ticker TSLA --method lstm
python main.py --ticker NVDA --method arima
```

### Method 3: With Features Selection
```bash
python main.py --ticker NVDA --features close volume
```

### Method 4: Custom Date Range
```bash
python main.py --ticker NVDA \
  --start-date 2023-01-01 \
  --end-date 2024-01-01 \
  --method arima
```

## 📈 Understanding Output

### Console Output Example
```
==============================================================================
TIME-SERIES STOCK PRICE FORECASTING ANALYSIS
==============================================================================

[STEP 1/7] Fetching stock data...
Fetching stock data for NVDA
Period: 2023-04-17 to 2024-04-17

============================================================
DATA SUMMARY FOR NVDA
============================================================
Company:        NVIDIA Corporation
Date Range:     2023-04-17 to 2024-04-17
Records:        252

Price Statistics:
  Start Price:   $285.50
  End Price:     $875.30
  Min Price:     $280.20
  Max Price:     $920.75
  Avg Price:     $580.40
  Change:        +206.36%
  Volatility:    42.15%
  Avg Volume:    62,450,000
============================================================
```

### Generated Files
```
output/
├── plots/
│   ├── NVDA_historical.png          <- Price history chart
│   ├── NVDA_forecast_prophet.png    <- Forecast with confidence bands
│   └── NVDA_decomposition.png       <- Trend/Seasonal breakdown
├── NVDA_forecast_report.txt         <- Detailed text report
└── NVDA_forecast_report.json        <- Machine-readable JSON
```

### Report Contents
```
EXECUTIVE SUMMARY
- Stock ticker and company name
- Current price and historical returns

DATA CHARACTERISTICS
- Stationarity: Is data mean-reverting or trending?
- Trend: Direction and strength
- Seasonality: Recurring patterns detected?
- Volatility: How much does price fluctuate?

SELECTED METHOD
- Why this method was chosen

FORECAST RESULTS
Table with dates, predicted prices, and confidence intervals:
  Date       Forecast    Lower 95%   Upper 95%
  2024-05-01 $172.50     $169.20     $175.80

MODEL METRICS
- RMSE, MAE, MAPE (prediction accuracy on historical data)

RISK ASSESSMENT
- Confidence interval widths
- Data-specific warnings
```

## 🎯 Choosing a Forecasting Method

| Situation | Recommended Method | Why |
|-----------|-------------------|-----|
| First time analyzing this stock | `auto` | Analyzes data and picks best method |
| Stock with clear trend | `linear_regression` or `prophet` | Captures uptrend/downtrend |
| Very volatile stock | `lstm` or `xgboost` | Handles complex patterns |
| Stock with seasonal patterns (weekly/monthly) | `prophet` or `exponential_smoothing` | Captures recurring patterns |
| Need fast analysis | `linear_regression` | Very fast (< 1 sec) |
| Want most accurate predictions | `lstm` or `xgboost` | Machine learning approaches |
| Classic time-series approach | `arima` | Statistical gold standard |

## 🧪 Try These Examples

### Example 1: Tech Stock with Auto-Selection
```bash
python main.py --ticker NVDA
# High volatility tech stock - recommender likely suggests LSTM or XGBoost
```

### Example 2: Stable Blue-Chip Stock
```bash
python main.py --ticker JNJ
# Stable health care company - recommender likely suggests Linear Regression or Prophet
```

### Example 3: Volatile Crypto-Related Stock
```bash
python main.py --ticker COIN --method lstm
# Crypto exchange - LSTM captures complex patterns
```

### Example 4: Compare Multiple Methods
```bash
# Run same analysis with different methods to compare
python main.py --ticker NVDA --method prophet
python main.py --ticker NVDA --method lstm
python main.py --ticker NVDA --method xgboost
# Check output/ for reports and plots from each method
```

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| "No data found for ticker" | Check spelling of ticker symbol |
| "ImportError: No module named 'prophet'" | Run `pip install -r requirements.txt` |
| "CUDA not available" (TensorFlow warning) | Normal - CPU will be used, just slower |
| Very wide confidence intervals | High uncertainty - recent data very volatile |
| Memory error | Close other apps or use simpler method |

## 📚 Next Steps

1. **Read the full README.md** - Comprehensive documentation
2. **Review example_usage.md** - Detailed usage guide
3. **Try example_analysis.py** - Run interactive examples
4. **Check output/plots/** - Visualize your predictions
5. **Analyze the text report** - Understand the forecast

## ⚠️ Important Reminders

- ✓ This is for educational analysis only
- ✓ Not investment advice
- ✓ Past performance ≠ future results
- ✓ Always consult financial advisors
- ✓ Consider multiple factors beyond technical forecast

## 🎓 Learning Resources

- **Linear Regression**: Simple trend-based baseline
- **ARIMA**: Classic statistical time-series (Box-Jenkins)
- **Prophet**: Handles seasonality with trend decomposition
- **LSTM**: Deep learning approach for complex sequences
- **XGBoost**: Ensemble method with feature interactions

---

**Ready to forecast?** Run your first analysis:
```bash
python main.py --ticker NVDA
```

Enjoy! 📈
