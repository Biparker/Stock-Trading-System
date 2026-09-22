#!/usr/bin/env python3
import yfinance as yf
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

tickers = ['ALAB', 'INTC', 'MU']

for ticker in tickers:
    print("\n" + "="*60)
    print(f"SCREENING: {ticker}")
    print("="*60)

    stock = yf.Ticker(ticker)
    info = stock.info

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
    roe           = info.get('returnOnEquity', 0) or 0

    print(f"Current Price:    ${price:.2f}")
    print(f"Market Cap:       ${market_cap:,.0f}")
    print(f"P/E (Trailing):   {pe_ratio:.2f}")
    print(f"P/E (Forward):    {fwd_pe:.2f}")
    print(f"Debt/Equity:      {debt_equity:.2f}")
    print(f"Profit Margin:    {profit_margin*100:.2f}%")
    print(f"Revenue Growth:   {rev_growth*100:.2f}%")
    print(f"ROE:              {roe*100:.2f}%")
    print(f"Beta:             {beta:.2f}")
    print(f"Analyst Rating:   {analyst_mean:.2f} (1=StrongBuy, 5=Sell)")
    print(f"Analyst Target:   ${target_price:.2f}")
    if price > 0 and target_price > 0:
        upside = (target_price - price) / price * 100
        print(f"Analyst Upside:   {upside:.1f}%")

    # Price momentum
    end_date   = datetime.now()
    start_date = end_date - timedelta(days=90)
    df = stock.history(start=start_date, end=end_date)

    if not df.empty and len(df) >= 30:
        ret_7d   = (df['Close'].iloc[-1] / df['Close'].iloc[-7]  - 1) * 100
        ret_30d  = (df['Close'].iloc[-1] / df['Close'].iloc[-30] - 1) * 100
        ret_90d  = (df['Close'].iloc[-1] / df['Close'].iloc[0]   - 1) * 100
        vol_daily = df['Close'].pct_change().std() * 100
        sma_20   = df['Close'].rolling(20).mean().iloc[-1]
        above    = price > sma_20
        print(f"7-Day Return:     {ret_7d:.2f}%")
        print(f"30-Day Return:    {ret_30d:.2f}%")
        print(f"90-Day Return:    {ret_90d:.2f}%")
        print(f"Daily Volatility: {vol_daily:.2f}%")
        print(f"Above 20d SMA:    {above}  (SMA=${sma_20:.2f})")
    else:
        ret_7d = ret_30d = ret_90d = vol_daily = 0
        above = False

    # Stability filter check
    pe_max = 50
    de_max = 3.0
    checks = {
        "Market Cap >= $10B":  market_cap >= 10_000_000_000,
        "Positive P/E":        pe_ratio > 0,
        "Profitable":          profit_margin > 0,
        f"P/E <= {pe_max}":    (pe_ratio <= pe_max) if pe_ratio > 0 else True,
        f"D/E <= {de_max}":    (debt_equity <= de_max) if debt_equity > 0 else True,
    }
    print()
    print("--- Stability Filter Results ---")
    all_pass = True
    for label, result in checks.items():
        status = "PASS" if result else "FAIL"
        if not result:
            all_pass = False
        print(f"  {label}: {status}")
    print(f"  OVERALL: {'PASS' if all_pass else 'FAIL'}")

print("\nDone.")
