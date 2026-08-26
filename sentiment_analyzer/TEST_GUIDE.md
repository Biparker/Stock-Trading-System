# Testing Guide - Sentiment Analyzer

## Safe Testing Procedure

### Step 1: Setup Credentials (On Your Computer)

```bash
cd stock-trading-system/sentiment_analyzer
python main.py --setup-credentials
```

When prompted, enter YOUR Merrill Lynch credentials. They will be encrypted and stored locally on YOUR computer only.

### Step 2: Test Download for Apple (AAPL)

```bash
python main.py --ticker AAPL --download-latest --verbose
```

This will:
1. Authenticate with your Merrill account
2. Navigate to research section
3. Download the latest Morningstar report for AAPL
4. Save it to `data/sample_reports/`

### Step 3: Analyze the Downloaded Report

```bash
python main.py --ticker AAPL --pdf-path "data/sample_reports/AAPL_morningstar_*.pdf" --report-format text
```

This will:
1. Extract text from the PDF
2. Analyze sentiment using FinBERT
3. Extract metrics (price target, rating, etc.)
4. Generate a comprehensive report
5. Save to `output/sentiment_reports/`

### Step 4: Review Results

Check the generated report:
```bash
# Windows
type output\sentiment_reports\AAPL_sentiment_report_*.txt

# Mac/Linux
cat output/sentiment_reports/AAPL_sentiment_report_*.txt
```

### Step 5: Generate Trading Signal (Optional)

```bash
python main.py --ticker AAPL \
  --pdf-path "data/sample_reports/AAPL_morningstar_*.pdf" \
  --integrate-trading \
  --technical-score 72.5 \
  --current-price 150.00
```

## Alternative: Test with Sample PDF

If you want to test without downloading:

### Option 1: Manual Download
1. Log into your Merrill account manually
2. Navigate to Research → Stocks → Enter AAPL
3. Find Morningstar report and download PDF
4. Save to `stock-trading-system/sentiment_analyzer/data/sample_reports/AAPL_report.pdf`

### Option 2: Analyze the Manual Download
```bash
python main.py --ticker AAPL --pdf-path "data/sample_reports/AAPL_report.pdf"
```

## Troubleshooting

### Issue: "ChromeDriver not found"
**Solution**: Download ChromeDriver from https://chromedriver.chromium.org/downloads
- Match your Chrome browser version
- Add to system PATH or place in project directory

### Issue: "Authentication failed"
**Possible causes**:
1. Incorrect credentials - Re-run `--setup-credentials`
2. 2FA enabled - May require manual intervention
3. Account locked - Check Merrill account status
4. Page structure changed - May need code updates

### Issue: "PDF extraction failed"
**Solutions**:
1. Verify PDF is not password-protected
2. Try different extraction method in config.py
3. Check if PDF is corrupted

### Issue: "Model download failed"
**Solutions**:
1. Check internet connection
2. Ensure ~2GB free disk space
3. Try using VADER model: `--model vader`

## Expected Output

### Successful Download
```
✓ Authenticated successfully
✓ Report downloaded: data/sample_reports/AAPL_morningstar_20260605.pdf
```

### Successful Analysis
```
=== Sentiment Analysis Summary for AAPL ===
Sentiment Score: 75.50 / 100
Classification: BULLISH
Confidence: 85.00%
Method: FINBERT
Price Target: $180.00
Analyst Rating: Buy
```

### Successful Trading Signal
```
=== Trading Signal for AAPL ===
Recommendation: BUY
Combined Score: 73.50
Position Multiplier: 1.15x

Rationale: Recommendation: BUY. Combined score of 73.5 (Technical: 72.5, Sentiment: 75.5). 
Analyst sentiment is bullish with 85% confidence. Price target implies 20.0% upside. 
Risk level: medium. Suggested position size multiplier: 1.15x.
```

## Security Reminders

- ✓ Run this on YOUR computer only
- ✓ Never share your credentials with anyone
- ✓ Credentials are encrypted and stored locally
- ✓ System only reads reports (cannot trade)
- ✓ Monitor your account for any suspicious activity

## Next Steps After Testing

1. Review the generated report in `output/sentiment_reports/`
2. Check the sentiment score and classification
3. Review extracted metrics (price target, rating)
4. Compare with your own analysis
5. Use in conjunction with technical analysis

## Batch Testing (Multiple Stocks)

```bash
python main.py --ticker-list AAPL MSFT GOOGL NVDA --download-latest
```

This will download and analyze reports for all specified tickers.

## Performance Expectations

- **Download**: 5-10 seconds per report
- **Analysis**: 10-30 seconds with FinBERT
- **Report Generation**: 1-2 seconds
- **Total**: ~30-45 seconds per stock

## Support

If you encounter issues:
1. Check `output/sentiment_analyzer.log` for detailed error messages
2. Review SECURITY.md for security best practices
3. Consult README.md for complete documentation
4. Verify all dependencies are installed: `pip install -r requirements.txt`

---

**Important**: This testing should be done on YOUR computer with YOUR credentials. Never share your financial login information with anyone, including AI assistants or support personnel.