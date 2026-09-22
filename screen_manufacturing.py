#!/usr/bin/env python3
import yfinance as yf
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

MFG_STOCKS = {
    'Aerospace/Defense':    ['BA', 'RTX', 'LMT', 'NOC', 'GD'],
    'Industrial Machinery': ['CAT', 'DE', 'EMR', 'ETN', 'PH'],
    'Diversified Industrial':['HON', 'GE', 'MMM', 'ITW', 'ROK'],
}

results = []

for sub, tickers in MFG_STOCKS.items():
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info

            market_cap    = info.get('marketCap', 0) or 0
            pe_ratio      = info.get('trailingPE', 0) or 0
            fwd_pe        = info.get('forwardPE', 0) or 0
            debt_equity   = info.get('debtToEquity', 0) or 0
            profit_margin = info.get('profitMargins', 0) or 0
            rev_growth    = info.get('revenueGrowth', 0) or 0
            beta          = info.get('beta', 1.0) or 1.0
            price         = info.get('currentPrice', 0) or 0
            analyst_mean  = info.get('recommendationMean', 0) or 0
            target_price  = info.get('targetMeanPrice', 0) or 0

            end_date   = datetime.now()
            start_date = end_date - timedelta(days=90)
            df = stock.history(start=start_date, end=end_date)

            ret_7d = ret_30d = ret_90d = vol = 0.0
            above_sma = False
            if not df.empty and len(df) >= 30:
                ret_7d    = (df['Close'].iloc[-1] / df['Close'].iloc[-7]  - 1) * 100
                ret_30d   = (df['Close'].iloc[-1] / df['Close'].iloc[-30] - 1) * 100
                ret_90d   = (df['Close'].iloc[-1] / df['Close'].iloc[0]   - 1) * 100
                vol       = df['Close'].pct_change().std() * 100
                sma_20    = df['Close'].rolling(20).mean().iloc[-1]
                above_sma = price > sma_20

            # Non-tech stability filters: pe_max=40, de_max=2.5
            pe_max = 40
            de_max = 2.5
            f1 = market_cap >= 10_000_000_000
            f2 = pe_ratio > 0
            f3 = profit_margin > 0
            f4 = (pe_ratio <= pe_max) if pe_ratio > 0 else True
            f5 = (debt_equity <= de_max) if debt_equity > 0 else True
            passes = all([f1, f2, f3, f4, f5])

            upside = ((target_price - price) / price * 100) if (price > 0 and target_price > 0) else 0.0

            results.append({
                'sub': sub, 'ticker': ticker, 'price': price,
                'mktcap_b': market_cap / 1e9,
                'pe': pe_ratio, 'fwd_pe': fwd_pe,
                'de': debt_equity, 'margin': profit_margin * 100,
                'revgrowth': rev_growth * 100, 'beta': beta,
                'analyst': analyst_mean, 'upside': upside,
                'r7': ret_7d, 'r30': ret_30d, 'r90': ret_90d,
                'vol': vol, 'above_sma': above_sma, 'passes': passes,
                'f1': f1, 'f2': f2, 'f3': f3, 'f4': f4, 'f5': f5,
            })
            print(f"  {ticker} done")
        except Exception as e:
            print(f"ERROR {ticker}: {e}")

# Print results table
header = (
    f"{'Ticker':<6} {'Sub-Sector':<22} {'Price':>8} {'MCap$B':>7} "
    f"{'P/E':>6} {'FwdPE':>6} {'D/E':>5} {'Margin%':>7} "
    f"{'RevGr%':>7} {'Beta':>5} {'Rate':>5} {'Upside%':>8} "
    f"{'7d%':>6} {'30d%':>6} {'90d%':>6} {'Vol%':>5}  Filter"
)
print()
print(header)
print('-' * len(header))

for r in results:
    status = 'PASS' if r['passes'] else 'FAIL'
    fails = []
    if not r['f1']: fails.append('MCap')
    if not r['f2']: fails.append('PE<0')
    if not r['f3']: fails.append('Loss')
    if not r['f4']: fails.append('PE>40')
    if not r['f5']: fails.append('DE>2.5')
    fail_str = ','.join(fails) if fails else 'ok'

    line = (
        f"{r['ticker']:<6} {r['sub']:<22} {r['price']:>8.2f} {r['mktcap_b']:>7.1f} "
        f"{r['pe']:>6.1f} {r['fwd_pe']:>6.1f} {r['de']:>5.1f} {r['margin']:>7.2f} "
        f"{r['revgrowth']:>7.2f} {r['beta']:>5.2f} {r['analyst']:>5.2f} {r['upside']:>8.1f} "
        f"{r['r7']:>6.2f} {r['r30']:>6.2f} {r['r90']:>6.2f} {r['vol']:>5.2f}  {status}({fail_str})"
    )
    print(line)

print()
passers = [r for r in results if r['passes']]
print(f"PASSED: {len(passers)}/{len(results)}")
for r in passers:
    print(f"  {r['ticker']:6} | P/E {r['pe']:.1f} | Margin {r['margin']:.1f}% | D/E {r['de']:.2f} | Upside {r['upside']:.1f}% | Analyst {r['analyst']:.2f}")
