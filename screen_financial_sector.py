#!/usr/bin/env python3
"""
Financial Sector Stock Screening
=================================
Identify top 3 banking/insurance stocks for inflationary, higher interest rate environment.

Screening Criteria:
1. Market cap > $50B (stability)
2. Strong balance sheet (Tier 1 capital ratio for banks)
3. Dividend yield > 2% (income in volatile markets)
4. P/E ratio < 15 (value in rising rate environment)
5. Recent performance and momentum
6. Analyst ratings
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============================================================================
# FINANCIAL SECTOR CANDIDATES
# ============================================================================

# Major Banks
BANKS = {
    'JPM': 'JPMorgan Chase',
    'BAC': 'Bank of America',
    'WFC': 'Wells Fargo',
    'C': 'Citigroup',
    'GS': 'Goldman Sachs',
    'MS': 'Morgan Stanley',
    'USB': 'U.S. Bancorp',
    'PNC': 'PNC Financial',
    'TFC': 'Truist Financial',
    'COF': 'Capital One'
}

# Major Insurance Companies
INSURANCE = {
    'BRK.B': 'Berkshire Hathaway',
    'PGR': 'Progressive',
    'TRV': 'Travelers',
    'ALL': 'Allstate',
    'AIG': 'American International Group',
    'MET': 'MetLife',
    'PRU': 'Prudential Financial',
    'AFL': 'Aflac',
    'CB': 'Chubb',
    'AXP': 'American Express'  # Financial services
}

ALL_FINANCIALS = {**BANKS, **INSURANCE}

# ============================================================================
# SCREENING FUNCTIONS
# ============================================================================

def get_stock_metrics(ticker):
    """Get key metrics for a financial stock."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get historical data for momentum
        hist = stock.history(period='1y')
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1]
        year_ago_price = hist['Close'].iloc[0]
        ytd_return = (current_price - year_ago_price) / year_ago_price * 100
        
        # 3-month momentum
        three_months_ago = hist['Close'].iloc[-63] if len(hist) >= 63 else hist['Close'].iloc[0]
        three_month_return = (current_price - three_months_ago) / three_months_ago * 100
        
        # Volatility
        returns = hist['Close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100  # Annualized
        
        metrics = {
            'ticker': ticker,
            'name': info.get('longName', ALL_FINANCIALS.get(ticker, 'Unknown')),
            'sector': info.get('sector', 'Financial'),
            'market_cap': info.get('marketCap', 0) / 1e9,  # in billions
            'current_price': current_price,
            'pe_ratio': info.get('trailingPE', None),
            'forward_pe': info.get('forwardPE', None),
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'payout_ratio': info.get('payoutRatio', 0) * 100 if info.get('payoutRatio') else 0,
            'beta': info.get('beta', None),
            'ytd_return': ytd_return,
            'three_month_return': three_month_return,
            'volatility': volatility,
            'book_value': info.get('bookValue', None),
            'price_to_book': info.get('priceToBook', None),
            'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else None,
            'debt_to_equity': info.get('debtToEquity', None),
            'analyst_rating': info.get('recommendationKey', 'none'),
            'target_price': info.get('targetMeanPrice', None),
            'num_analysts': info.get('numberOfAnalystOpinions', 0)
        }
        
        return metrics
        
    except Exception as e:
        print(f"  [ERROR] {ticker}: {str(e)}")
        return None


def calculate_composite_score(metrics):
    """
    Calculate composite score for financial stocks in rising rate environment.
    
    Scoring factors:
    - Market cap (stability): 15%
    - Valuation (P/E, P/B): 20%
    - Dividend yield: 15%
    - ROE: 15%
    - Momentum (3-month): 15%
    - Analyst rating: 10%
    - Low volatility: 10%
    """
    score = 0
    max_score = 100
    
    # 1. Market Cap Score (15 points) - Prefer large caps
    if metrics['market_cap'] >= 200:
        score += 15
    elif metrics['market_cap'] >= 100:
        score += 12
    elif metrics['market_cap'] >= 50:
        score += 8
    else:
        score += 3
    
    # 2. Valuation Score (20 points) - Lower P/E and P/B better
    pe_score = 0
    if metrics['forward_pe'] and metrics['forward_pe'] > 0:
        if metrics['forward_pe'] < 10:
            pe_score = 10
        elif metrics['forward_pe'] < 12:
            pe_score = 8
        elif metrics['forward_pe'] < 15:
            pe_score = 6
        else:
            pe_score = 3
    
    pb_score = 0
    if metrics['price_to_book'] and metrics['price_to_book'] > 0:
        if metrics['price_to_book'] < 1.0:
            pb_score = 10
        elif metrics['price_to_book'] < 1.5:
            pb_score = 8
        elif metrics['price_to_book'] < 2.0:
            pb_score = 6
        else:
            pb_score = 3
    
    score += pe_score + pb_score
    
    # 3. Dividend Yield Score (15 points)
    if metrics['dividend_yield'] >= 4:
        score += 15
    elif metrics['dividend_yield'] >= 3:
        score += 12
    elif metrics['dividend_yield'] >= 2:
        score += 8
    else:
        score += 3
    
    # 4. ROE Score (15 points) - Higher is better
    if metrics['roe'] and metrics['roe'] > 0:
        if metrics['roe'] >= 15:
            score += 15
        elif metrics['roe'] >= 12:
            score += 12
        elif metrics['roe'] >= 10:
            score += 8
        else:
            score += 5
    
    # 5. Momentum Score (15 points) - 3-month return
    if metrics['three_month_return'] >= 10:
        score += 15
    elif metrics['three_month_return'] >= 5:
        score += 12
    elif metrics['three_month_return'] >= 0:
        score += 8
    elif metrics['three_month_return'] >= -5:
        score += 5
    else:
        score += 2
    
    # 6. Analyst Rating Score (10 points)
    rating_map = {
        'strong buy': 10,
        'buy': 8,
        'outperform': 8,
        'hold': 5,
        'underperform': 2,
        'sell': 0
    }
    score += rating_map.get(metrics['analyst_rating'].lower(), 5)
    
    # 7. Volatility Score (10 points) - Lower is better
    if metrics['volatility'] < 20:
        score += 10
    elif metrics['volatility'] < 25:
        score += 8
    elif metrics['volatility'] < 30:
        score += 6
    else:
        score += 3
    
    return score


# ============================================================================
# MAIN SCREENING
# ============================================================================

def main():
    """Run financial sector screening."""
    print("="*80)
    print("FINANCIAL SECTOR STOCK SCREENING")
    print("="*80)
    print("\nEnvironment: Inflationary, Higher Interest Rates, Geopolitical Risk")
    print("Target: Top 3 Banking/Insurance Stocks")
    print(f"\nScreening {len(ALL_FINANCIALS)} financial stocks...")
    print("="*80)
    
    results = []
    
    for ticker, name in ALL_FINANCIALS.items():
        print(f"\nAnalyzing {ticker} ({name})...")
        metrics = get_stock_metrics(ticker)
        
        if metrics:
            metrics['composite_score'] = calculate_composite_score(metrics)
            results.append(metrics)
            print(f"  [OK] Score: {metrics['composite_score']:.1f}/100")
        else:
            print(f"  [SKIP] Unable to retrieve data")
    
    # Sort by composite score
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('composite_score', ascending=False)
    
    # Display results
    print("\n" + "="*80)
    print("SCREENING RESULTS - TOP 10")
    print("="*80)
    
    print("\n{:<6} {:<30} {:>10} {:>8} {:>8} {:>8} {:>8} {:>8}".format(
        "Rank", "Stock", "Score", "Mkt Cap", "P/E", "Div %", "ROE %", "3M Ret"
    ))
    print("-"*80)
    
    for idx, row in results_df.head(10).iterrows():
        print("{:<6} {:<30} {:>10.1f} {:>8.1f}B {:>8.1f} {:>8.1f} {:>8.1f} {:>8.1f}%".format(
            results_df.index.get_loc(idx) + 1,
            f"{row['ticker']} - {row['name'][:20]}",
            row['composite_score'],
            row['market_cap'],
            row['forward_pe'] if row['forward_pe'] else row['pe_ratio'] if row['pe_ratio'] else 0,
            row['dividend_yield'],
            row['roe'] if row['roe'] else 0,
            row['three_month_return']
        ))
    
    # Top 3 recommendations
    print("\n" + "="*80)
    print("TOP 3 RECOMMENDATIONS")
    print("="*80)
    
    top3 = results_df.head(3)
    
    for idx, (_, row) in enumerate(top3.iterrows(), 1):
        print(f"\n{idx}. {row['ticker']} - {row['name']}")
        print(f"   Composite Score: {row['composite_score']:.1f}/100")
        print(f"   Market Cap: ${row['market_cap']:.1f}B")
        print(f"   Current Price: ${row['current_price']:.2f}")
        print(f"   P/E Ratio: {row['forward_pe']:.1f}" if row['forward_pe'] else f"   P/E Ratio: {row['pe_ratio']:.1f}" if row['pe_ratio'] else "   P/E Ratio: N/A")
        print(f"   Dividend Yield: {row['dividend_yield']:.2f}%")
        print(f"   ROE: {row['roe']:.1f}%" if row['roe'] else "   ROE: N/A")
        print(f"   YTD Return: {row['ytd_return']:+.2f}%")
        print(f"   3-Month Return: {row['three_month_return']:+.2f}%")
        print(f"   Volatility: {row['volatility']:.1f}%")
        print(f"   Analyst Rating: {row['analyst_rating'].title()}")
        print(f"   Target Price: ${row['target_price']:.2f}" if row['target_price'] else "   Target Price: N/A")
        
        # Upside potential
        if row['target_price']:
            upside = (row['target_price'] - row['current_price']) / row['current_price'] * 100
            print(f"   Upside Potential: {upside:+.1f}%")
    
    # Save results
    results_df.to_csv('financial_sector_screening.csv', index=False)
    print("\n" + "="*80)
    print("[OK] Results saved to: financial_sector_screening.csv")
    print("="*80)
    
    # Generate summary report
    generate_report(top3)
    
    return top3


def generate_report(top3):
    """Generate detailed report for top 3 stocks."""
    
    report = f"""# Financial Sector Stock Screening Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Environment:** Inflationary, Higher Interest Rates, Geopolitical Risk  
**Sector:** Banking & Insurance  
**Objective:** Identify top 3 stocks for current market conditions

---

## Market Environment Analysis

### Why Financial Stocks Now?

**Inflationary Environment:**
- Banks benefit from higher interest rates → increased net interest margins
- Insurance companies earn more on investment portfolios
- Pricing power to pass costs to customers

**Higher Interest Rates:**
- Banks: Wider lending spreads = higher profitability
- Insurance: Better returns on float and reserves
- Value stocks (financials) outperform growth in rising rate environment

**Geopolitical Risk:**
- Flight to quality → established financial institutions
- Increased demand for insurance products
- Defensive characteristics of large-cap financials

---

## Top 3 Recommendations

"""
    
    for idx, (_, row) in enumerate(top3.iterrows(), 1):
        upside = ""
        if row['target_price']:
            upside_pct = (row['target_price'] - row['current_price']) / row['current_price'] * 100
            upside = f" (Upside: {upside_pct:+.1f}%)"
        
        report += f"""
### {idx}. {row['ticker']} - {row['name']}

**Composite Score:** {row['composite_score']:.1f}/100

**Key Metrics:**
- Market Cap: ${row['market_cap']:.1f}B
- Current Price: ${row['current_price']:.2f}
- Target Price: ${row['target_price']:.2f}{upside if row['target_price'] else ' (N/A)'}
- P/E Ratio: {row['forward_pe']:.1f if row['forward_pe'] else row['pe_ratio']:.1f if row['pe_ratio'] else 'N/A'}
- Price-to-Book: {row['price_to_book']:.2f if row['price_to_book'] else 'N/A'}
- Dividend Yield: {row['dividend_yield']:.2f}%
- ROE: {row['roe']:.1f if row['roe'] else 0}%

**Performance:**
- YTD Return: {row['ytd_return']:+.2f}%
- 3-Month Return: {row['three_month_return']:+.2f}%
- Volatility: {row['volatility']:.1f}%
- Beta: {row['beta']:.2f if row['beta'] else 'N/A'}

**Analyst Opinion:**
- Rating: {row['analyst_rating'].title()}
- Number of Analysts: {row['num_analysts']}

**Why This Stock:**
"""
        
        # Add specific rationale based on metrics
        if row['dividend_yield'] >= 3:
            report += f"- ✓ Strong dividend yield ({row['dividend_yield']:.2f}%) provides income cushion\n"
        
        if row['roe'] and row['roe'] >= 12:
            report += f"- ✓ High ROE ({row['roe']:.1f}%) indicates efficient capital deployment\n"
        
        if row['forward_pe'] and row['forward_pe'] < 12:
            report += f"- ✓ Attractive valuation (Forward P/E: {row['forward_pe']:.1f})\n"
        elif row['pe_ratio'] and row['pe_ratio'] < 12:
            report += f"- ✓ Attractive valuation (P/E: {row['pe_ratio']:.1f})\n"
        
        if row['three_month_return'] > 0:
            report += f"- ✓ Positive momentum ({row['three_month_return']:+.1f}% 3-month return)\n"
        
        if row['market_cap'] >= 100:
            report += f"- ✓ Large-cap stability (${row['market_cap']:.1f}B market cap)\n"
        
        if row['volatility'] < 25:
            report += f"- ✓ Lower volatility ({row['volatility']:.1f}%) for defensive positioning\n"
        
        report += "\n---\n"
    
    report += """
## Investment Strategy

### Position Sizing
- Allocate equally across top 3 (33% each) for diversification
- Or weight by composite score for conviction-based allocation

### Entry Strategy
- Enter on dips of 2-3% below current price
- Use weekly review cycle with 2% stop loss
- Target 3% profit-taking levels

### Risk Management
- Stop loss: 2% below entry
- Position size: 0.8x-1.0x based on individual risk tolerance
- Monitor quarterly earnings and Fed policy announcements

### Time Horizon
- Short-term (1-3 months): Benefit from rate environment
- Medium-term (3-6 months): Capture earnings growth
- Long-term (6-12 months): Dividend income + capital appreciation

---

## Sector Outlook

**Positive Catalysts:**
- Continued rate hikes → higher net interest margins
- Strong loan demand in recovering economy
- Insurance pricing power in hard market
- Dividend growth from strong earnings

**Risks to Monitor:**
- Recession fears → loan loss provisions
- Inverted yield curve → margin compression
- Regulatory changes → capital requirements
- Credit quality deterioration

**Recommendation:** Financial sector offers attractive risk-reward in current environment. Top 3 stocks provide exposure with quality, value, and income characteristics.

---

**Disclaimer:** This analysis is for informational purposes only. Past performance does not guarantee future results. Consult a financial advisor before making investment decisions.

**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Script:** screen_financial_sector.py
"""
    
    # Save report
    with open('FINANCIAL_SECTOR_SCREENING_REPORT.md', 'w') as f:
        f.write(report)
    
    print("[OK] Report saved to: FINANCIAL_SECTOR_SCREENING_REPORT.md")


if __name__ == "__main__":
    top3 = main()
    print("\n[COMPLETE] Financial sector screening finished!")

# Made with Bob
