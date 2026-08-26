# Sentiment Analyzer - Quick Start Guide

Get started with the Stock Sentiment Analysis Agent in minutes.

## Installation

### 1. Navigate to Directory
```bash
cd stock-trading-system/sentiment_analyzer
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** First installation may take 5-10 minutes as it downloads the FinBERT model (~400MB).

### 4. Install ChromeDriver (for PDF download)
Download ChromeDriver matching your Chrome version from:
https://chromedriver.chromium.org/downloads

Add to your system PATH or place in the project directory.

## Initial Setup

### Configure Credentials
```bash
python main.py --setup-credentials
```

Enter your Merrill Lynch username and password. Credentials are encrypted and stored locally.

## Basic Usage

### Analyze Existing PDF
```bash
python main.py --ticker AAPL --pdf-path "data/sample_reports/AAPL_report.pdf"
```

### Download and Analyze Latest Report
```bash
python main.py --ticker MSFT --download-latest
```

### Generate Different Report Formats
```bash
# Text report (default)
python main.py --ticker AAPL --pdf-path "report.pdf"

# JSON report
python main.py --ticker AAPL --pdf-path "report.pdf" --report-format json

# HTML report
python main.py --ticker AAPL --pdf-path "report.pdf" --report-format html
```

### Generate Trading Signal
```bash
python main.py --ticker AAPL \
  --pdf-path "report.pdf" \
  --integrate-trading \
  --technical-score 72.5 \
  --current-price 150.00
```

### Batch Analysis
```bash
python main.py --ticker-list AAPL MSFT GOOGL NVDA --download-latest
```

## Output Locations

- **Reports**: `output/sentiment_reports/`
- **Trading Signals**: `output/trading_signals/`
- **Logs**: `output/sentiment_analyzer.log`
- **Downloaded PDFs**: `data/sample_reports/`

## Quick Examples

### Example 1: Complete Analysis with Chart
```bash
python main.py \
  --ticker AAPL \
  --pdf-path "data/sample_reports/AAPL_morningstar_20260605.pdf" \
  --report-format html \
  --generate-chart
```

### Example 2: Trading Integration
```bash
python main.py \
  --ticker MSFT \
  --download-latest \
  --integrate-trading \
  --technical-score 68.0 \
  --current-price 420.00 \
  --report-format json
```

### Example 3: Batch with Custom Model
```bash
python main.py \
  --ticker-list AAPL MSFT GOOGL AMZN \
  --download-latest \
  --model vader \
  --report-format text
```

## Programmatic Usage

```python
from src import SentimentEngine, ReportGenerator, TradingIntegrator

# Analyze a report
engine = SentimentEngine()
result = engine.analyze_report('path/to/report.pdf')

# Generate report
generator = ReportGenerator()
report_path = generator.generate_report(result, 'text')

# Generate trading signal
integrator = TradingIntegrator()
signal = integrator.generate_trading_signal(
    ticker='AAPL',
    technical_score=72.5,
    current_price=150.00
)

print(f"Recommendation: {signal['recommendation']}")
print(f"Sentiment Score: {signal['sentiment_score']:.2f}")
```

## Common Issues

### "ChromeDriver not found"
- Download ChromeDriver and add to PATH
- Or specify path in config.py

### "Authentication failed"
- Verify Merrill Lynch credentials
- Check if 2FA is enabled (may require manual intervention)
- Ensure account has research access

### "Model download failed"
- Check internet connection
- Ensure sufficient disk space (~2GB)
- Try using `--model vader` as fallback

### "PDF extraction failed"
- Verify PDF is not password-protected
- Check PDF format compatibility
- Try different extraction method in config.py

## Next Steps

1. Review full documentation in `README.md`
2. Explore configuration options in `src/config.py`
3. Check example outputs in `output/` directory
4. Integrate with your trading system

## Support

For detailed documentation, see:
- `README.md` - Complete documentation
- `src/config.py` - Configuration options
- `output/sentiment_analyzer.log` - Detailed logs

---

**B. I. Parker Data Science and Consulting LLC**