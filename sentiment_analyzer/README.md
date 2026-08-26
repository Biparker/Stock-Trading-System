# Stock Sentiment Analysis Agent

An intelligent agent system for analyzing sentiment from Morningstar analyst reports downloaded from Merrill Lynch accounts. This tool extracts, processes, and analyzes PDF reports to provide actionable sentiment insights for stock trading decisions.

## Features

### 🤖 Intelligent Agent System
- **PDF Retrieval Agent**: Automatically downloads Morningstar analyst reports from Merrill Lynch account
- **PDF Extraction Agent**: Extracts and processes text from PDF documents
- **Sentiment Analysis Agent**: Analyzes report content using NLP and financial sentiment models
- **Trading Integration Agent**: Incorporates sentiment scores into trading recommendations

### 📊 Analysis Capabilities
1. **Overall Sentiment Score** - Bullish, Neutral, or Bearish classification with confidence scores
2. **Key Metrics Extraction** - Price targets, ratings, earnings estimates
3. **Risk Assessment** - Identifies risk factors and concerns mentioned in reports
4. **Recommendation Strength** - Quantifies analyst conviction levels
5. **Historical Tracking** - Tracks sentiment changes over time

### 📈 Trading Integration
- **Sentiment-Weighted Scoring**: Combines technical analysis with sentiment scores
- **Risk-Adjusted Recommendations**: Modifies position sizing based on sentiment confidence
- **Alert System**: Notifies on significant sentiment changes
- **Multi-Source Aggregation**: Combines multiple analyst reports for consensus view

## Architecture

```
sentiment_analyzer/
├── src/
│   ├── __init__.py
│   ├── config.py                    # Configuration settings
│   ├── pdf_retriever.py             # Merrill account PDF download
│   ├── pdf_extractor.py             # PDF text extraction
│   ├── sentiment_engine.py          # Core sentiment analysis
│   ├── metrics_extractor.py         # Extract financial metrics
│   ├── report_generator.py          # Generate sentiment reports
│   ├── trading_integrator.py        # Integrate with trading system
│   └── main_analyzer.py             # Main orchestrator
├── tests/
│   ├── __init__.py
│   ├── test_pdf_extraction.py
│   ├── test_sentiment_engine.py
│   └── test_integration.py
├── data/
│   ├── sample_reports/              # Sample Morningstar PDFs
│   └── credentials/                 # Encrypted credentials (gitignored)
├── output/
│   ├── sentiment_reports/           # Generated sentiment analysis
│   └── trading_signals/             # Trading recommendations
├── models/                          # Pre-trained sentiment models
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Merrill Lynch account credentials
- Access to Morningstar research reports

### Setup

1. Navigate to the sentiment_analyzer directory:
```bash
cd stock-trading-system/sentiment_analyzer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure credentials:
```bash
python main.py --setup-credentials
```

## Usage

### Interactive Mode
```bash
python main.py
```

### Command Line Mode

**Analyze a specific stock:**
```bash
python main.py --ticker AAPL --download-latest
```

**Analyze existing PDF:**
```bash
python main.py --ticker MSFT --pdf-path "path/to/report.pdf"
```

**Batch analysis:**
```bash
python main.py --ticker-list AAPL MSFT GOOGL NVDA --download-latest
```

**Generate trading signals:**
```bash
python main.py --ticker AAPL --integrate-trading
```

## Output

### Sentiment Report Structure
```
SENTIMENT ANALYSIS REPORT
- Stock ticker and company name
- Report date and analyst information
- Overall sentiment score (0-100)
- Sentiment classification (Bullish/Neutral/Bearish)
- Confidence level

KEY METRICS
- Price target and current price
- Analyst rating (Buy/Hold/Sell)
- Earnings estimates
- Revenue projections

SENTIMENT BREAKDOWN
- Positive factors (with scores)
- Negative factors (with scores)
- Risk factors identified
- Opportunities highlighted

HISTORICAL COMPARISON
- Previous sentiment scores
- Sentiment trend direction
- Rating changes

TRADING RECOMMENDATION
- Recommended action (Buy/Hold/Sell)
- Position size adjustment
- Risk level assessment
- Integration with technical analysis
```

## Configuration

Edit `src/config.py` to adjust:
- Merrill Lynch API endpoints
- Sentiment scoring thresholds
- NLP model parameters
- Trading integration weights
- Report generation settings

## Security

### Credential Management
- Credentials stored encrypted using `cryptography` library
- Environment variables supported for CI/CD
- Never commit credentials to version control
- Use `.env` file for local development (gitignored)

### Best Practices
- Rotate credentials regularly
- Use read-only API access when possible
- Enable two-factor authentication on Merrill account
- Monitor API usage for anomalies

## Integration with Trading System

### Sentiment Score Integration
The sentiment score (0-100) is integrated into the trading system's decision matrix:

```python
# Example integration
from sentiment_analyzer.src.trading_integrator import SentimentIntegrator

integrator = SentimentIntegrator()
sentiment_score = integrator.get_sentiment_score('AAPL')

# Adjust position sizing based on sentiment
if sentiment_score > 70:  # Strong bullish
    position_multiplier = 1.2
elif sentiment_score < 30:  # Strong bearish
    position_multiplier = 0.5
else:  # Neutral
    position_multiplier = 1.0
```

### Combined Scoring System
```
Final Score = (Technical Score * 0.6) + (Sentiment Score * 0.4)
```

## Sentiment Analysis Methods

### 1. FinBERT Model
- Pre-trained on financial text
- Specialized for financial sentiment
- High accuracy on analyst reports

### 2. Keyword-Based Analysis
- Financial lexicon matching
- Context-aware scoring
- Industry-specific terminology

### 3. Metrics Extraction
- Regex patterns for price targets
- Rating classification
- Earnings estimate parsing

### 4. Risk Factor Detection
- Identifies cautionary language
- Quantifies risk mentions
- Categorizes risk types

## API Reference

### PDF Retriever
```python
from src.pdf_retriever import PDFRetriever

retriever = PDFRetriever(username='user', password='pass')
pdf_path = retriever.download_report('AAPL', report_type='morningstar')
```

### Sentiment Engine
```python
from src.sentiment_engine import SentimentEngine

engine = SentimentEngine()
result = engine.analyze_report(pdf_path='report.pdf')
print(f"Sentiment: {result['sentiment_score']}")
```

### Trading Integrator
```python
from src.trading_integrator import TradingIntegrator

integrator = TradingIntegrator()
recommendation = integrator.generate_recommendation(
    ticker='AAPL',
    sentiment_score=75,
    technical_score=68
)
```

## Limitations

- **Report Availability**: Depends on Merrill Lynch access and Morningstar coverage
- **PDF Format Variations**: Different report formats may require parsing adjustments
- **Sentiment Subjectivity**: NLP models may misinterpret nuanced language
- **Timeliness**: Reports may be dated; always check publication date
- **Single Source**: Morningstar only; consider multiple analyst sources

## Important Disclaimers

⚠️ **This tool is for informational purposes only.**

- Sentiment analysis is one factor among many in investment decisions
- Analyst reports reflect opinions, not guarantees
- Past analyst accuracy does not predict future performance
- Always conduct your own due diligence
- Consult with a financial advisor before making investment decisions
- The authors assume no liability for any financial losses

## Troubleshooting

### Common Issues

**"Authentication failed"**
- Verify Merrill Lynch credentials
- Check if account has research access
- Ensure two-factor authentication is configured

**"PDF extraction failed"**
- Verify PDF is not password-protected
- Check PDF format compatibility
- Try manual text extraction

**"No sentiment detected"**
- Verify PDF contains analyst commentary
- Check if report is in supported format
- Review extracted text for completeness

## Advanced Features

### Custom Sentiment Models
Train custom models on your historical data:
```bash
python main.py --train-model --training-data "path/to/labeled_data.csv"
```

### Sentiment Tracking Dashboard
Launch web dashboard for visualization:
```bash
python main.py --dashboard --port 8080
```

### Automated Monitoring
Set up scheduled report downloads:
```bash
python main.py --schedule --frequency daily --tickers AAPL MSFT GOOGL
```

## Version History

### v1.0.0 (Initial Release)
- PDF retrieval from Merrill Lynch
- Text extraction from Morningstar reports
- FinBERT-based sentiment analysis
- Metrics extraction (price targets, ratings)
- Trading system integration
- Comprehensive reporting

## Support

For issues or questions:
- Review troubleshooting section
- Check example outputs in `output/` directory
- Examine test files for usage examples
- Ensure all dependencies are installed

---

**Developed by B. I. Parker Data Science and Consulting LLC**
**Part of the Automated Stock Trading System**