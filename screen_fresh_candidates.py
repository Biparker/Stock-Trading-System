#!/usr/bin/env python3
"""Screen for a fresh candidate -- excludes already-tested tickers."""
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import sys
warnings.filterwarnings('ignore')
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

ALREADY_TESTED = {
    'AAPL','JPM','BAC','WFC','MU','META','INTC','QCOM','NVDA','AMD',
    'GOOGL','AMZN','UNH','ABT','ABBV','PNC'
}

POOL = [
    # Technology
    'MSFT','AVGO','ORCL','CSCO','ADBE','CRM','TXN','AMAT','IBM','KLAC',
    # Healthcare
    'LLY','MRK','TMO','DHR','PFE','BMY','AMGN','GILD','CI','HUM','CVS',
    # Financial
    'GS','MS','C','BLK','SCHW','AXP','USB','TFC','COF','BK',
    # Consumer / Industrial
    'COST','HD','LOW','WMT','NKE','CAT','HON','DE',
]
POOL = [t for t in POOL if t not in ALREADY_TESTED]

print(f'Screening {len(POOL)} candidates...\n')
print(f'{"TICKER":<8} {"SCORE":>5}  {"P/E":>6}  {"MARGIN":>7}  {"30d RET":>8}  {"VOL":>5}  PRICE')
print('-' * 65)

results = []
for ticker in POOL:
    try:
        stk  = yf.Ticker(ticker)
        info = stk.info
        end  = datetime.now()
        hist = stk.history(start=end - timedelta(days=95), end=end)
        if hist.empty or len(hist) < 30:
            continue

        mc  = info.get('marketCap', 0)
        pe  = info.get('trailingPE', 0) or 0
        pm  = info.get('profitMargins', 0) or 0
        px  = float(hist['Close'].iloc[-1])
        r30 = (hist['Close'].iloc[-1] / hist['Close'].iloc[-30] - 1) * 100
        vol = hist['Close'].pct_change().std() * 100

        if mc < 10e9 or pe <= 0 or pm <= 0:
            continue

        score = 0
        if mc >= 100e9:    score += 30
        elif mc >= 50e9:   score += 20
        else:              score += 10

        if 0 < pe <= 25:   score += 25
        elif pe <= 35:     score += 15
        elif pe <= 50:     score += 5

        if pm > 0.20:      score += 20
        elif pm > 0.10:    score += 15
        elif pm > 0.05:    score += 10

        if r30 > 10:       score += 20
        elif r30 > 5:      score += 15
        elif r30 > 0:      score += 10
        elif r30 > -5:     score += 5

        if vol < 1.5:      score += 10
        elif vol < 2.5:    score += 5

        results.append({
            'ticker': ticker, 'score': score,
            'pe': pe, 'pm': pm * 100, 'r30': r30, 'vol': vol, 'px': px
        })
    except Exception as e:
        print(f'  [{ticker}] error: {e}')

results.sort(key=lambda x: x['score'], reverse=True)

for r in results[:12]:
    print(f"{r['ticker']:<8} {r['score']:>5}  {r['pe']:>6.1f}  {r['pm']:>6.1f}%  "
          f"{r['r30']:>+7.2f}%  {r['vol']:>4.2f}%  ${r['px']:.2f}")

print()
print('TOP 3 FRESH CANDIDATES:')
for i, r in enumerate(results[:3], 1):
    print(f"  {i}. {r['ticker']}  score={r['score']}  30d={r['r30']:+.2f}%  "
          f"P/E={r['pe']:.1f}  margin={r['pm']:.1f}%  ${r['px']:.2f}")
