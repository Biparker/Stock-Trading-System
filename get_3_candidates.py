#!/usr/bin/env python3
"""
Quick script to get 3 candidate stocks based on the trading system methodology.
Simplified version that focuses on getting results.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Top stocks from Technology, Healthcare, and Financial sectors
CANDIDATE_POOL = [
    # Technology
    'AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META', 'AVGO', 'ORCL', 'CSCO', 'ADBE', 'CRM',
    'INTC', 'AMD', 'QCOM', 'TXN', 'AMAT',
    # Healthcare
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY',
    'AMGN', 'GILD', 'CVS', 'CI', 'HUM',
    # Financial (Banks/Insurance)
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'USB',
    'PNC', 'TFC', 'COF', 'BK', 'STT'
]


def get_stock_score(ticker):
    """Calculate a simple composite score for ranking."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get historical data for momentum
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty or len(hist) < 20:
            return None
        
        # Calculate metrics
        market_cap = info.get('marketCap', 0)
        pe_ratio = info.get('trailingPE', 0)
        profit_margin = info.get('profitMargins', 0)
        
        # Calculate momentum
        returns_30d = (hist['Close'].iloc[-1] / hist['Close'].iloc[-30] - 1) * 100 if len(hist) >= 30 else 0
        volatility = hist['Close'].pct_change().std() * 100
        
        # Simple scoring
        score = 0
        
        # Market cap score (prefer large cap)
        if market_cap >= 100_000_000_000:
            score += 30
        elif market_cap >= 50_000_000_000:
            score += 20
        elif market_cap >= 10_000_000_000:
            score += 10
        
        # P/E score (prefer reasonable valuations)
        if 0 < pe_ratio <= 25:
            score += 25
        elif 0 < pe_ratio <= 35:
            score += 15
        elif 0 < pe_ratio <= 50:
            score += 5
        
        # Profitability score
        if profit_margin > 0.20:
            score += 20
        elif profit_margin > 0.10:
            score += 15
        elif profit_margin > 0.05:
            score += 10
        
        # Momentum score
        if returns_30d > 5:
            score += 15
        elif returns_30d > 0:
            score += 10
        elif returns_30d > -5:
            score += 5
        
        # Volatility penalty
        if volatility < 2:
            score += 10
        elif volatility < 3:
            score += 5
        
        return {
            'ticker': ticker,
            'score': score,
            'market_cap': market_cap,
            'pe_ratio': pe_ratio,
            'profit_margin': profit_margin * 100,
            'returns_30d': returns_30d,
            'volatility': volatility,
            'current_price': info.get('currentPrice', hist['Close'].iloc[-1])
        }
    
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None


def main():
    print("\n" + "="*70)
    print("GENERATING 3 CANDIDATE STOCKS FOR TRADING SYSTEM")
    print("="*70)
    print(f"\nAnalyzing {len(CANDIDATE_POOL)} stocks from Technology, Healthcare & Financial sectors...")
    print()
    
    results = []
    for i, ticker in enumerate(CANDIDATE_POOL, 1):
        print(f"[{i}/{len(CANDIDATE_POOL)}] Analyzing {ticker}...", end=' ')
        result = get_stock_score(ticker)
        if result:
            results.append(result)
            print(f"Score: {result['score']}")
        else:
            print("SKIPPED")
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Get top 3
    top_3 = results[:3]
    
    print("\n" + "="*70)
    print("TOP 3 CANDIDATE STOCKS")
    print("="*70)
    print()
    
    for i, stock in enumerate(top_3, 1):
        print(f"{i}. {stock['ticker']:6s} - Score: {stock['score']:3.0f} | "
              f"P/E: {stock['pe_ratio']:6.2f} | "
              f"Margin: {stock['profit_margin']:5.2f}% | "
              f"30d Return: {stock['returns_30d']:+6.2f}% | "
              f"Price: ${stock['current_price']:7.2f}")
    
    print("\n" + "="*70)
    print("MERRILL LYNCH ORDER TIMING REMINDER:")
    print("  Step 1 - BUY: Place market/limit purchase order")
    print("  Step 2 - TRAILING STOP: Wait AT LEAST 24 hours (next trading day)")
    print("           after purchase before placing trailing stop sell order.")
    print("           Same-day sell orders risk a FREE RIDE VIOLATION.")
    print("           Set a calendar reminder at time of purchase.")
    print("="*70)
    print("\nNEXT STEP: Run backtesting on each candidate to determine optimal stop loss %")
    print("Command: python weekly_stop_loss_backtest.py --ticker <TICKER>")
    print("="*70)
    
    # Save to file
    output_file = 'candidate_stocks_list.txt'
    with open(output_file, 'w') as f:
        f.write(f"3 CANDIDATE STOCKS - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        f.write("Based on Trading System Methodology:\n")
        f.write("- Sector Selection: Technology, Healthcare & Financial\n")
        f.write("- Screening: Market Cap ($10B+), Profitability, Valuation\n")
        f.write("- Ranking: Composite score (fundamentals + momentum + risk)\n\n")
        f.write("="*70 + "\n\n")
        f.write("MERRILL LYNCH ORDER TIMING REMINDER:\n")
        f.write("  Step 1 - BUY: Place market/limit purchase order\n")
        f.write("  Step 2 - TRAILING STOP: Wait AT LEAST 24 hours (next trading day)\n")
        f.write("           after purchase before placing trailing stop sell order.\n")
        f.write("           Same-day sell orders risk a FREE RIDE VIOLATION.\n")
        f.write("           Set a calendar reminder at time of purchase.\n\n")
        f.write("="*70 + "\n\n")
        f.write("NEXT STEP: Backtest each candidate with 1 year of data to determine\n")
        f.write("optimal stop loss percentage (2-5%) for each stock.\n\n")
        f.write("="*70 + "\n\n")
        
        for i, stock in enumerate(top_3, 1):
            f.write(f"{i}. {stock['ticker']} (Composite Score: {stock['score']:.0f})\n")
            f.write(f"   Market Cap: ${stock['market_cap']:,.0f}\n")
            f.write(f"   P/E Ratio: {stock['pe_ratio']:.2f}\n")
            f.write(f"   Profit Margin: {stock['profit_margin']:.2f}%\n")
            f.write(f"   30-Day Return: {stock['returns_30d']:+.2f}%\n")
            f.write(f"   Volatility: {stock['volatility']:.2f}%\n")
            f.write(f"   Current Price: ${stock['current_price']:.2f}\n")
            f.write(f"   ** REQUIRES BACKTESTING FOR STOP LOSS % **\n\n")
    
    print(f"\nResults saved to: {output_file}")
    print("\nThese 3 stocks require backtesting to determine optimal stop loss %.")
    print()


if __name__ == "__main__":
    main()

# Made with Bob
