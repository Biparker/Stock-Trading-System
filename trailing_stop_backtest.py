"""
Trailing Stop Loss Backtesting Analysis
========================================
Monte Carlo simulation testing TRAILING STOP LOSS ONLY.

Tests multiple trailing stop percentages: 2%, 3%, 4%, 5%
Compares performance to find optimal trailing stop level.

Based on empirical data from time_series_analyzer backtesting results.

Usage: python trailing_stop_backtest.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import json

# Set random seed for reproducibility
np.random.seed(42)

# ============================================================================
# EMPIRICAL PARAMETERS FROM BACKTESTING
# ============================================================================

# From 90_DAY_TESTING_STATISTICAL_ANALYSIS.md
INITIAL_CAPITAL = 1000
N_WEEKS = 12  # 90 days ≈ 12-13 weeks
MEAN_WEEKLY_RETURN = 0.0097  # 0.97%
STD_WEEKLY_RETURN = 0.0425   # 4.25%
TRAILING_STOP_LEVELS = [0.02, 0.03, 0.04, 0.05]  # 2%, 3%, 4%, 5%
PROFIT_TARGET = 0.03         # 3% profit target
N_SIMULATIONS = 5000

# ============================================================================
# SIMULATION FUNCTIONS
# ============================================================================

def run_trailing_stop_simulation(stop_loss_pct, n_sims=N_SIMULATIONS):
    """
    Trailing stop loss approach: Stop adjusts upward with price, never down
    Locks in profits automatically while maintaining downside protection
    
    Parameters:
    - stop_loss_pct: Trailing stop percentage (e.g., 0.02 for 2%)
    """
    results = []
    stop_loss_triggers = []
    
    for sim in range(n_sims):
        capital = INITIAL_CAPITAL
        highest_capital = INITIAL_CAPITAL  # Track peak value
        stops_triggered = 0
        
        # 12 weekly periods
        for week in range(N_WEEKS):
            # Simulate weekly return
            weekly_return = np.random.normal(MEAN_WEEKLY_RETURN, STD_WEEKLY_RETURN)
            
            # Apply return
            capital *= (1 + weekly_return)
            
            # Update highest capital achieved (peak tracking)
            highest_capital = max(highest_capital, capital)
            
            # Trailing stop: trigger if drop from peak exceeds threshold
            drawdown_from_peak = (capital - highest_capital) / highest_capital
            
            if drawdown_from_peak <= -stop_loss_pct:
                # Stop triggered - reset position
                capital = INITIAL_CAPITAL
                highest_capital = INITIAL_CAPITAL
                stops_triggered += 1
            
            # Apply profit target (cap weekly gains)
            if capital > highest_capital * (1 + PROFIT_TARGET):
                capital = highest_capital * (1 + PROFIT_TARGET)
                highest_capital = capital
        
        results.append(capital)
        stop_loss_triggers.append(stops_triggered)
    
    return np.array(results), np.array(stop_loss_triggers)


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def calculate_statistics(results, label):
    """Calculate comprehensive statistics for simulation results"""
    returns = (results - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    stats = {
        'label': label,
        'mean': results.mean(),
        'median': np.median(results),
        'std': results.std(),
        'min': results.min(),
        'max': results.max(),
        'mean_return_pct': returns.mean(),
        'median_return_pct': np.median(returns),
        'std_return_pct': returns.std(),
        'percentiles': {
            '10th': np.percentile(results, 10),
            '25th': np.percentile(results, 25),
            '50th': np.percentile(results, 50),
            '75th': np.percentile(results, 75),
            '90th': np.percentile(results, 90),
        },
        'probabilities': {
            'positive': np.mean(returns > 0) * 100,
            'above_5pct': np.mean(returns > 5) * 100,
            'above_10pct': np.mean(returns > 10) * 100,
            'above_15pct': np.mean(returns > 15) * 100,
            'above_20pct': np.mean(returns > 20) * 100,
            'below_0pct': np.mean(returns < 0) * 100,
            'below_minus5pct': np.mean(returns < -5) * 100,
            'below_minus10pct': np.mean(returns < -10) * 100,
        }
    }
    
    return stats


def calculate_risk_metrics(results):
    """Calculate risk-adjusted performance metrics"""
    returns = (results - INITIAL_CAPITAL) / INITIAL_CAPITAL
    
    # Sharpe Ratio (assuming risk-free rate of 0.04/12 per week)
    risk_free_rate = 0.04 / 12 * N_WEEKS  # Annualized 4% scaled to 12 weeks
    excess_return = returns.mean() - risk_free_rate
    sharpe_ratio = excess_return / returns.std() if returns.std() > 0 else 0
    
    # Sortino Ratio (downside deviation)
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else returns.std()
    sortino_ratio = excess_return / downside_std if downside_std > 0 else 0
    
    # Maximum Drawdown
    cumulative_returns = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min() * 100
    
    # Value at Risk (95% confidence)
    var_95 = np.percentile(returns, 5) * 100
    
    return {
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown_pct': max_drawdown,
        'var_95_pct': var_95,
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run complete trailing stop backtesting analysis"""
    
    print("=" * 70)
    print("TRAILING STOP LOSS BACKTESTING ANALYSIS")
    print("=" * 70)
    print(f"\nRunning {N_SIMULATIONS:,} Monte Carlo simulations per trailing stop level...")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"Testing Period: {N_WEEKS} weeks (90 days)")
    print(f"Trailing Stop Levels: {[f'{x*100:.0f}%' for x in TRAILING_STOP_LEVELS]}")
    print(f"Profit Target: {PROFIT_TARGET*100}%\n")
    
    # Run simulations for each trailing stop level
    results_by_level = {}
    
    for i, stop_pct in enumerate(TRAILING_STOP_LEVELS, 1):
        print(f"{i}. Running trailing stop simulation at {stop_pct*100:.0f}%...")
        results, stops = run_trailing_stop_simulation(stop_pct)
        
        # Calculate statistics
        stats = calculate_statistics(results, f"Trailing Stop {stop_pct*100:.0f}%")
        risk = calculate_risk_metrics(results)
        
        results_by_level[f"{stop_pct*100:.0f}%"] = {
            'stop_pct': stop_pct,
            'results': results,
            'stops': stops,
            'statistics': stats,
            'risk_metrics': risk
        }
        
        print(f"   Sharpe Ratio: {risk['sharpe_ratio']:.3f}")
        print(f"   Mean Return: {stats['mean_return_pct']:+.2f}%")
        print(f"   P(Loss > 5%): {stats['probabilities']['below_minus5pct']:.2f}%")
        print(f"   Avg Stops/Year: {stops.mean():.1f}\n")
    
    # Determine optimal trailing stop
    print(f"\n{len(TRAILING_STOP_LEVELS)+1}. Determining optimal trailing stop level...")
    best_stop = None
    best_sharpe = -999
    
    for stop_label, data in results_by_level.items():
        risk = data['risk_metrics']
        stats = data['statistics']
        
        # Check if meets criteria
        meets_sharpe = risk['sharpe_ratio'] > 0.3
        meets_downside = stats['probabilities']['below_minus5pct'] < 5.0
        meets_stops = 8 <= data['stops'].mean() <= 16
        
        if meets_sharpe and meets_downside:
            if risk['sharpe_ratio'] > best_sharpe:
                best_sharpe = risk['sharpe_ratio']
                best_stop = stop_label
    
    # Print comparison table
    print("\n" + "=" * 70)
    print("TRAILING STOP COMPARISON TABLE")
    print("=" * 70)
    print(f"\n{'Stop %':<10} {'Sharpe':<10} {'Mean Ret':<12} {'P(Loss>5%)':<14} {'Stops/Yr':<10} {'Status':<10}")
    print("-" * 70)
    
    for stop_label, data in results_by_level.items():
        m = data['statistics']
        r = data['risk_metrics']
        marker = " *OPTIMAL*" if stop_label == best_stop else ""
        print(f"{stop_label:<10} {r['sharpe_ratio']:<10.3f} {m['mean_return_pct']:>+10.2f}% "
              f"{m['probabilities']['below_minus5pct']:>12.2f}% {data['stops'].mean():>9.1f}{marker}")
    
    print("-" * 70)
    
    if best_stop:
        best_data = results_by_level[best_stop]
        best_metrics = best_data['statistics']
        best_risk = best_data['risk_metrics']
        
        print(f"\n✅ RECOMMENDED TRAILING STOP: {best_stop}")
        print(f"\nPERFORMANCE AT RECOMMENDED LEVEL:")
        print(f"  - Sharpe Ratio: {best_risk['sharpe_ratio']:.3f}")
        print(f"  - Sortino Ratio: {best_risk['sortino_ratio']:.3f}")
        print(f"  - Mean Return: {best_metrics['mean_return_pct']:+.2f}%")
        print(f"  - Median Return: {best_metrics['median_return_pct']:+.2f}%")
        print(f"  - P(Profit): {best_metrics['probabilities']['positive']:.1f}%")
        print(f"  - P(Loss > 5%): {best_metrics['probabilities']['below_minus5pct']:.2f}%")
        print(f"  - Expected Stops/Year: {best_data['stops'].mean():.1f}")
        print(f"\n✅ USE {best_stop} TRAILING STOP for Stage 2 backtesting")
    else:
        print(f"\n❌ NO TRAILING STOP LEVEL MEETS ALL CRITERIA")
    
    # Save results to JSON
    print(f"\n{len(TRAILING_STOP_LEVELS)+2}. Saving results...")
    results_data = {
        'simulation_parameters': {
            'initial_capital': INITIAL_CAPITAL,
            'n_weeks': N_WEEKS,
            'mean_weekly_return': MEAN_WEEKLY_RETURN,
            'std_weekly_return': STD_WEEKLY_RETURN,
            'trailing_stop_levels': TRAILING_STOP_LEVELS,
            'profit_target': PROFIT_TARGET,
            'n_simulations': N_SIMULATIONS,
        },
        'recommended_trailing_stop': best_stop,
        'results_by_level': {}
    }
    
    # Convert numpy arrays to lists for JSON serialization
    for stop_label, data in results_by_level.items():
        results_data['results_by_level'][stop_label] = {
            'stop_pct': data['stop_pct'],
            'statistics': data['statistics'],
            'risk_metrics': data['risk_metrics'],
            'stop_triggers': {
                'mean': float(data['stops'].mean()),
                'max': int(data['stops'].max()),
                'pct_no_stops': float(np.sum(data['stops'] == 0) / len(data['stops']) * 100)
            }
        }
    
    json_filename = 'stock-trading-system/trailing_stop_results.json'
    with open(json_filename, 'w') as f:
        json.dump(results_data, f, indent=2)
    print(f"[OK] Saved results: {json_filename}")
    
    print("\n" + "=" * 70)
    print("Analysis complete!")
    print(f"Results saved to: {json_filename}")
    print("=" * 70)


if __name__ == "__main__":
    main()

# Made with Bob