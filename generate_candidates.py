#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate 7 Candidate Stocks for Trading System
Based on sector selection, screening, and ranking methodology
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import warnings
import sys
warnings.filterwarnings('ignore')

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


# Sector definitions from TRADING_SYSTEM_PLAN.md
SECTOR_STOCKS = {
    'Technology': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META', 'AVGO', 'ORCL', 'CSCO', 'ADBE', 'CRM', 'INTC', 'AMD', 'QCOM', 'TXN', 'AMAT'],
    'Healthcare': ['UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY', 'AMGN', 'GILD', 'CVS', 'CI', 'HUM'],
    'Financial Services': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'USB', 'PNC', 'TFC', 'COF', 'BK', 'STT'],
    'Consumer': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'COST', 'WMT', 'DIS', 'BKNG', 'MAR', 'CMG'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL', 'KMI', 'WMB', 'HES', 'DVN', 'FANG'],
}


def get_stock_data(ticker: str, days: int = 90) -> pd.DataFrame:
    """Fetch stock data for analysis."""
    try:
        stock = yf.Ticker(ticker)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        df = stock.history(start=start_date, end=end_date)
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()


def get_atr_pct(df: pd.DataFrame, period: int = 14) -> float:
    """Return 14-day ATR as a percentage of the most recent close price.

    Uses the standard true-range formula:
        TR = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    Returns 0.0 if there is insufficient data.
    """
    if df.empty or len(df) < period + 1:
        return 0.0
    high  = df['High']
    low   = df['Low']
    close = df['Close']
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    current_price = close.iloc[-1]
    if current_price <= 0:
        return 0.0
    return float(atr / current_price * 100)


def get_20day_return(df: pd.DataFrame) -> float:
    """Return the 20-trading-day price return as a percentage.

    Returns -999.0 (always filtered) if there is insufficient data.
    """
    if df.empty or len(df) < 21:
        return -999.0
    return float((df['Close'].iloc[-1] / df['Close'].iloc[-21] - 1) * 100)


def get_fundamental_data(ticker: str) -> Dict:
    """Get fundamental metrics for screening."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            'ticker': ticker,
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'debt_to_equity': info.get('debtToEquity', 0),
            'current_ratio': info.get('currentRatio', 0),
            'profit_margin': info.get('profitMargins', 0),
            'revenue_growth': info.get('revenueGrowth', 0),
            'beta': info.get('beta', 1.0),
            'current_price': info.get('currentPrice', 0),
        }
    except Exception as e:
        print(f"Error getting fundamentals for {ticker}: {e}")
        return None


def passes_stability_filters(fundamentals: Dict, sector: str = 'Technology') -> bool:
    """Apply stability screening filters."""
    if not fundamentals:
        return False

    # Sector-specific adjustments
    pe_max = 50 if sector == 'Technology' else 40
    # yfinance returns debtToEquity as a percentage (e.g. 29.1 means 0.291 ratio)
    # so thresholds are expressed in those same percentage-point units
    de_max = 300.0 if sector == 'Technology' else 250.0

    # Apply filters - more lenient for real-world data
    checks = [
        fundamentals['market_cap'] >= 10_000_000_000,  # $10B minimum
        fundamentals['pe_ratio'] > 0,  # Must have positive P/E
        fundamentals['profit_margin'] > 0,  # Must be profitable
    ]

    # Optional checks (don't fail if missing)
    if fundamentals['pe_ratio'] > 0:
        checks.append(fundamentals['pe_ratio'] <= pe_max)
    if fundamentals['debt_to_equity'] > 0:
        checks.append(fundamentals['debt_to_equity'] <= de_max)

    return all(checks)


def calculate_momentum_score(df: pd.DataFrame) -> float:
    """Calculate momentum/trend score (0-100)."""
    if df.empty or len(df) < 20:
        return 0
    
    try:
        # Calculate returns
        returns_7d = (df['Close'].iloc[-1] / df['Close'].iloc[-7] - 1) * 100
        returns_30d = (df['Close'].iloc[-1] / df['Close'].iloc[-30] - 1) * 100
        
        # Calculate volatility (lower is better)
        volatility = df['Close'].pct_change().std() * 100
        
        # Simple momentum score
        momentum = (returns_7d * 0.4 + returns_30d * 0.6) / 2
        volatility_penalty = max(0, 20 - volatility)
        
        score = max(0, min(100, 50 + momentum + volatility_penalty))
        return score
    except:
        return 0


def calculate_composite_score(ticker: str, fundamentals: Dict, df: pd.DataFrame) -> float:
    """Calculate composite ranking score based on TRADING_SYSTEM_PLAN.md."""
    if df.empty:
        return 0
    
    # Forecast Performance (40%) - using momentum as proxy
    forecast_score = calculate_momentum_score(df) * 0.40
    
    # Risk Metrics (30%) - lower volatility and beta is better
    volatility = df['Close'].pct_change().std() * 100
    beta = fundamentals.get('beta', 1.0)
    risk_score = max(0, (100 - volatility * 10) * 0.5 + (100 - abs(beta - 1) * 50) * 0.5) * 0.30
    
    # Fundamental Strength (20%)
    pe_score = max(0, 100 - fundamentals.get('pe_ratio', 30))
    margin_score = fundamentals.get('profit_margin', 0) * 1000
    fundamental_score = (pe_score * 0.5 + margin_score * 0.5) * 0.20
    
    # Technical Indicators (10%) - simple price trend
    sma_20 = df['Close'].rolling(20).mean().iloc[-1]
    price = df['Close'].iloc[-1]
    technical_score = (100 if price > sma_20 else 50) * 0.10
    
    composite = forecast_score + risk_score + fundamental_score + technical_score
    return composite


def generate_candidates(selected_sectors: List[str] = None, num_candidates: int = 7) -> List[Tuple[str, float, Dict]]:
    """
    Generate ranked list of candidate stocks.

    Args:
        selected_sectors: List of sectors to analyze (default: Technology, Healthcare)
        num_candidates: Number of top candidates to return (default: 7)

    Returns:
        List of tuples: (ticker, composite_score, fundamentals)
        fundamentals now includes 'atr_pct' (14-day ATR as % of price) and
        'return_20d' (20-day price return %) used for MeLLeA volatility-scaled sizing.
    """
    if selected_sectors is None:
        selected_sectors = ['Technology', 'Healthcare']

    print(f"\n{'='*70}")
    print(f"GENERATING {num_candidates} CANDIDATE STOCKS")
    print(f"{'='*70}")
    print(f"Selected Sectors: {', '.join(selected_sectors)}")
    print(f"\nPhase 1: Collecting stock universe...")

    # Collect all stocks from selected sectors — deduplicate so a ticker that
    # appears in multiple sector lists is only evaluated once.
    seen: set = set()
    stock_universe = []
    for sector in selected_sectors:
        for ticker in SECTOR_STOCKS.get(sector, []):
            if ticker not in seen:
                seen.add(ticker)
                stock_universe.append(ticker)

    print(f"Total stocks to analyze: {len(stock_universe)}")

    # Phase 2: Screen for stability
    print(f"\nPhase 2: Applying stability filters...")
    screened_stocks = []

    for ticker in stock_universe:
        print(f"  Analyzing {ticker}...", end=' ')
        fundamentals = get_fundamental_data(ticker)

        if fundamentals and passes_stability_filters(fundamentals, selected_sectors[0]):
            screened_stocks.append((ticker, fundamentals))
            print("[PASSED]")
        else:
            print("[FILTERED]")

    print(f"\nStocks passing filters: {len(screened_stocks)}")

    # Phase 3: Rank by composite score + apply 20-day momentum filter
    print(f"\nPhase 3: Calculating composite scores (momentum filter active)...")
    ranked_stocks = []

    for ticker, fundamentals in screened_stocks:
        print(f"  Scoring {ticker}...", end=' ')
        df = get_stock_data(ticker)

        if df.empty:
            print("[NO DATA]")
            continue

        # ── 20-day momentum filter ────────────────────────────────────────────
        ret_20d = get_20day_return(df)
        if ret_20d < 0:
            print(f"[MOMENTUM FILTER] 20d return={ret_20d:.2f}% — skipped")
            continue

        # ── ATR% for volatility-scaled sizing ────────────────────────────────
        atr_pct = get_atr_pct(df)
        fundamentals['atr_pct']    = round(atr_pct, 4)
        fundamentals['return_20d'] = round(ret_20d, 4)

        score = calculate_composite_score(ticker, fundamentals, df)
        ranked_stocks.append((ticker, score, fundamentals))
        print(f"Score: {score:.2f}  ATR%: {atr_pct:.2f}  20d: {ret_20d:+.2f}%")

    # Sort by score (descending)
    ranked_stocks.sort(key=lambda x: x[1], reverse=True)

    # Return top N candidates
    top_candidates = ranked_stocks[:num_candidates]
    
    print(f"\n{'='*70}")
    print(f"TOP {num_candidates} CANDIDATE STOCKS")
    print(f"{'='*70}\n")
    
    for i, (ticker, score, fundamentals) in enumerate(top_candidates, 1):
        print(f"{i}. {ticker:6s} - Score: {score:6.2f} | "
              f"P/E: {fundamentals['pe_ratio']:6.2f} | "
              f"Margin: {fundamentals['profit_margin']*100:5.2f}% | "
              f"Price: ${fundamentals['current_price']:7.2f}")
    
    print(f"\n{'='*70}")
    print("MERRILL LYNCH ORDER TIMING REMINDER:")
    print("  Step 1 - BUY: Place market/limit purchase order")
    print("  Step 2 - TRAILING STOP: Wait AT LEAST 24 hours (next trading day)")
    print("           after purchase before placing trailing stop sell order.")
    print("           Placing a sell order same-day risks a FREE RIDE VIOLATION.")
    print("           Set a calendar reminder at time of purchase.")
    print(f"{'='*70}\n")
    
    return top_candidates


def main():
    """Main execution function."""
    # Example: Generate candidates from Technology and Healthcare sectors
    candidates = generate_candidates(
        selected_sectors=['Technology', 'Healthcare'],
        num_candidates=7
    )
    
    # Save to file
    output_file = 'candidate_stocks.txt'
    with open(output_file, 'w') as f:
        f.write(f"7 Candidate Stocks - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        f.write("MERRILL LYNCH ORDER TIMING REMINDER:\n")
        f.write("  Step 1 - BUY: Place market/limit purchase order\n")
        f.write("  Step 2 - TRAILING STOP: Wait AT LEAST 24 hours (next trading day)\n")
        f.write("           after purchase before placing trailing stop sell order.\n")
        f.write("           Same-day sell orders risk a FREE RIDE VIOLATION.\n")
        f.write("           Set a calendar reminder at time of purchase.\n\n")
        f.write("="*70 + "\n\n")
        for i, (ticker, score, fundamentals) in enumerate(candidates, 1):
            f.write(f"{i}. {ticker} (Score: {score:.2f})\n")
            f.write(f"   Market Cap: ${fundamentals['market_cap']:,.0f}\n")
            f.write(f"   P/E Ratio: {fundamentals['pe_ratio']:.2f}\n")
            f.write(f"   Profit Margin: {fundamentals['profit_margin']*100:.2f}%\n")
            f.write(f"   Current Price: ${fundamentals['current_price']:.2f}\n\n")
    
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()

# Made with Bob
