"""
Stock-Specific Stop Loss Backtesting
=====================================
Tests multiple stop loss levels for individual stocks using historical data.

Usage: python stock_specific_backtest.py --ticker MSFT
"""

import numpy as np
import pandas as pd
import yfinance as yf
import argparse
from datetime import datetime, timedelta
import json

# Set random seed for reproducibility
np.random.seed(42)

# Configuration
STOP_LOSS_LEVELS = [0.02, 0.03, 0.05]  # 2%, 3%, 5%
N_SIMULATIONS = 5000
INITIAL_CAPITAL = 1000
LOOKBACK_DAYS = 252  # 1 year of trading days


def fetch_stock_data(ticker, days=LOOKBACK_DAYS):
    """Fetch historical stock data from Yahoo Finance"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 30)  # Extra buffer
    
    print(f"\n[STEP 1/4] Fetching {ticker} data from Yahoo Finance...")
    stock = yf.Ticker(ticker)
    df = stock.history(start=start_date, end=end_date)
    
    if len(df) < days:
        print(f"Warning: Only {len(df)} days of data available (requested {days})")
    
    # Calculate daily returns
    df['Returns'] = df['Close'].pct_change()
    df = df.dropna()
    
    print(f"[OK] Fetched {len(df)} days of data")
    print(f"     Price range: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
    print(f"     Mean daily return: {df['Returns'].mean()*100:.3f}%")
    print(f"     Daily volatility: {df['Returns'].std()*100:.3f}%")
    
    return df


def run_backtest_simulation(returns, stop_loss_pct, n_sims=N_SIMULATIONS):
    """
    Run Monte Carlo simulation with specific stop loss level.
    Uses actual historical return distribution.
    """
    results = []
    stop_triggers = []
    
    # Use empirical return distribution
    mean_return = returns.mean()
    std_return = returns.std()
    
    for sim in range(n_sims):
        capital = INITIAL_CAPITAL
        stops = 0
        
        # Simulate 252 trading days (1 year)
        for day in range(252):
            # Sample from historical return distribution
            daily_return = np.random.normal(mean_return, std_return)
            
            # Apply return
            capital *= (1 + daily_return)
            
            # Check stop loss (weekly review - check every 5 days)
            if day % 5 == 0:
                week_return = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL
                if week_return <= -stop_loss_pct:
                    # Stop loss triggered - reset to initial capital
                    capital = INITIAL_CAPITAL
                    stops += 1
        
        results.append(capital)
        stop_triggers.append(stops)
    
    return np.array(results), np.array(stop_triggers)


def calculate_metrics(results, stop_triggers):
    """Calculate performance metrics"""
    returns = (results - INITIAL_CAPITAL) / INITIAL_CAPITAL
    
    # Return statistics
    mean_return = returns.mean()
    median_return = np.median(returns)
    std_return = returns.std()
    
    # Risk metrics
    sharpe_ratio = mean_return / std_return if std_return > 0 else 0
    
    # Downside deviation (for Sortino)
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else std_return
    sortino_ratio = mean_return / downside_std if downside_std > 0 else 0
    
    # Probabilities
    p_positive = (returns > 0).sum() / len(returns) * 100
    p_loss_gt_5 = (returns < -0.05).sum() / len(returns) * 100
    
    # Stop loss activity
    avg_stops = stop_triggers.mean()
    
    return {
        'mean_return_pct': mean_return * 100,
        'median_return_pct': median_return * 100,
        'std_return_pct': std_return * 100,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'p_positive': p_positive,
        'p_loss_gt_5': p_loss_gt_5,
        'avg_stops_per_year': avg_stops,
        'final_capital_mean': results.mean(),
        'final_capital_median': np.median(results)
    }


def main():
    parser = argparse.ArgumentParser(description='Stock-specific stop loss backtesting')
    parser.add_argument('--ticker', required=True, help='Stock ticker symbol')
    args = parser.parse_args()
    
    ticker = args.ticker.upper()
    
    print("="*70)
    print(f"STOCK-SPECIFIC STOP LOSS BACKTESTING - {ticker}")
    print("="*70)
    
    # Fetch data
    df = fetch_stock_data(ticker)
    returns = df['Returns']
    
    # Test each stop loss level
    print(f"\n[STEP 2/4] Testing {len(STOP_LOSS_LEVELS)} stop loss levels...")
    print(f"     Simulations per level: {N_SIMULATIONS:,}")
    
    results_by_level = {}
    
    for stop_pct in STOP_LOSS_LEVELS:
        print(f"\n  Testing {stop_pct*100:.0f}% stop loss...")
        final_capitals, stop_triggers = run_backtest_simulation(returns, stop_pct)
        metrics = calculate_metrics(final_capitals, stop_triggers)
        
        results_by_level[f"{stop_pct*100:.0f}%"] = {
            'stop_loss_pct': stop_pct * 100,
            'metrics': metrics
        }
        
        print(f"    Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        print(f"    Mean Return: {metrics['mean_return_pct']:+.2f}%")
        print(f"    P(Loss > 5%): {metrics['p_loss_gt_5']:.2f}%")
        print(f"    Avg Stops/Year: {metrics['avg_stops_per_year']:.1f}")
    
    # Determine optimal stop loss
    print(f"\n[STEP 3/4] Determining optimal stop loss for {ticker}...")
    
    # Find stop loss with best Sharpe ratio that meets criteria
    best_stop = None
    best_sharpe = -999
    
    for stop_label, data in results_by_level.items():
        metrics = data['metrics']
        
        # Check if meets criteria
        meets_sharpe = metrics['sharpe_ratio'] > 0.3
        meets_downside = metrics['p_loss_gt_5'] < 5.0
        meets_stops = 8 <= metrics['avg_stops_per_year'] <= 16
        
        if meets_sharpe and meets_downside:
            if metrics['sharpe_ratio'] > best_sharpe:
                best_sharpe = metrics['sharpe_ratio']
                best_stop = stop_label
    
    # Generate report
    print(f"\n[STEP 4/4] Generating report...")
    
    print("\n" + "="*70)
    print(f"BACKTESTING RESULTS FOR {ticker}")
    print("="*70)
    
    print("\nCOMPARISON TABLE:")
    print("-" * 70)
    print(f"{'Stop Loss':<12} {'Sharpe':<10} {'Mean Ret':<12} {'P(Loss>5%)':<14} {'Stops/Yr':<10}")
    print("-" * 70)
    
    for stop_label, data in results_by_level.items():
        m = data['metrics']
        marker = " *" if stop_label == best_stop else ""
        print(f"{stop_label:<12} {m['sharpe_ratio']:<10.3f} {m['mean_return_pct']:>+10.2f}% "
              f"{m['p_loss_gt_5']:>12.2f}% {m['avg_stops_per_year']:>9.1f}{marker}")
    
    print("-" * 70)
    
    if best_stop:
        best_metrics = results_by_level[best_stop]['metrics']
        print(f"\n* RECOMMENDED STOP LOSS: {best_stop}")
        print(f"\nPERFORMANCE AT RECOMMENDED LEVEL:")
        print(f"  - Sharpe Ratio: {best_metrics['sharpe_ratio']:.3f}")
        print(f"  - Sortino Ratio: {best_metrics['sortino_ratio']:.3f}")
        print(f"  - Mean Return: {best_metrics['mean_return_pct']:+.2f}%")
        print(f"  - Median Return: {best_metrics['median_return_pct']:+.2f}%")
        print(f"  - P(Profit): {best_metrics['p_positive']:.1f}%")
        print(f"  - P(Loss > 5%): {best_metrics['p_loss_gt_5']:.2f}%")
        print(f"  - Expected Stops/Year: {best_metrics['avg_stops_per_year']:.1f}")
        
        # Stage 2 pass/fail
        passes_stage2 = (
            best_metrics['sharpe_ratio'] > 0.3 and
            best_metrics['p_loss_gt_5'] < 5.0 and
            8 <= best_metrics['avg_stops_per_year'] <= 16
        )
        
        print(f"\n{'='*70}")
        if passes_stage2:
            print(f"* {ticker} PASSES STAGE 2 - Proceed to Stage 3 (Sentiment Analysis)")
        else:
            print(f"X {ticker} FAILS STAGE 2 - Do not proceed to Stage 3")
        print(f"{'='*70}")
        
    else:
        print(f"\nX NO STOP LOSS LEVEL MEETS CRITERIA")
        print(f"X {ticker} FAILS STAGE 2 - Do not proceed to Stage 3")
    
    # Save results
    output_file = f"{ticker}_backtest_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'ticker': ticker,
            'date': datetime.now().isoformat(),
            'recommended_stop_loss': best_stop,
            'results_by_level': results_by_level
        }, f, indent=2)
    
    print(f"\n[OK] Results saved to: {output_file}")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()

# Made with Bob
