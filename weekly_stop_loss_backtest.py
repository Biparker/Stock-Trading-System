"""
Trailing Stop Loss Backtesting Analysis
========================================
Monte Carlo simulation with weekly review cycles and trailing stop loss strategy.

This script tests TRAILING STOP LOSS ONLY (no fixed stops).

Trailing stop levels tested: 2.0%, 3.0%, 4.0%, 5.0%
Compares different trailing stop percentages to find optimal level.

Based on empirical data from time_series_analyzer backtesting results.
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

# Stock performance data from backtesting
STOCKS = {
    'AAPL': {'forecast_36d': 0.1290, 'mape': 0.0101, 'volatility': 0.0148, 'r_squared': 0.6866},
    'NVDA': {'forecast_36d': 0.0414, 'mape': 0.0786, 'volatility': 0.0215, 'r_squared': 0.5491},
    'IBM':  {'forecast_36d': 0.1034, 'mape': 0.0826, 'volatility': 0.0206, 'r_squared': 0.0289},
}

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


def run_no_stop_loss_simulation(n_sims=N_SIMULATIONS):
    """
    Baseline: No stop loss for comparison
    """
    results = []
    
    for sim in range(n_sims):
        capital = INITIAL_CAPITAL
        
        for week in range(N_WEEKS):
            weekly_return = np.random.normal(MEAN_WEEKLY_RETURN, STD_WEEKLY_RETURN)
            
            # Only apply profit target, no stop loss
            weekly_return = min(weekly_return, PROFIT_TARGET)
            
            capital *= (1 + weekly_return)
        
        results.append(capital)
    
    return np.array(results)


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
# VISUALIZATION FUNCTIONS
# ============================================================================

def plot_distributions(fixed_results, trailing_results, hybrid_results, no_stop_results):
    """Create distribution comparison plots"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # Convert to returns
    fixed_returns = (fixed_results - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    trailing_returns = (trailing_results - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    hybrid_returns = (hybrid_results - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    no_stop_returns = (no_stop_results - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # Plot 1: Distribution comparison
    axes[0, 0].hist(fixed_returns, bins=50, alpha=0.4, label='Fixed Stop', color='blue')
    axes[0, 0].hist(trailing_returns, bins=50, alpha=0.4, label='Trailing Stop', color='green')
    axes[0, 0].hist(hybrid_returns, bins=50, alpha=0.4, label='Hybrid Stop', color='purple')
    axes[0, 0].hist(no_stop_returns, bins=50, alpha=0.3, label='No Stop', color='red')
    axes[0, 0].axvline(fixed_returns.mean(), color='blue', linestyle='--', linewidth=2)
    axes[0, 0].axvline(trailing_returns.mean(), color='green', linestyle='--', linewidth=2)
    axes[0, 0].axvline(hybrid_returns.mean(), color='purple', linestyle='--', linewidth=2)
    axes[0, 0].set_xlabel('Return (%)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Return Distribution Comparison')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Cumulative distribution
    sorted_fixed = np.sort(fixed_returns)
    sorted_trailing = np.sort(trailing_returns)
    sorted_hybrid = np.sort(hybrid_returns)
    sorted_no_stop = np.sort(no_stop_returns)
    cumulative = np.arange(1, len(sorted_fixed) + 1) / len(sorted_fixed) * 100
    
    axes[0, 1].plot(sorted_fixed, cumulative, label='Fixed Stop', linewidth=2)
    axes[0, 1].plot(sorted_trailing, cumulative, label='Trailing Stop', linewidth=2)
    axes[0, 1].plot(sorted_hybrid, cumulative, label='Hybrid Stop', linewidth=2)
    axes[0, 1].plot(sorted_no_stop, cumulative, label='No Stop', linewidth=2, alpha=0.5)
    axes[0, 1].set_xlabel('Return (%)')
    axes[0, 1].set_ylabel('Cumulative Probability (%)')
    axes[0, 1].set_title('Cumulative Distribution Function')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Box plot comparison
    data_to_plot = [fixed_returns, trailing_returns, hybrid_returns, no_stop_returns]
    axes[1, 0].boxplot(data_to_plot, labels=['Fixed', 'Trailing', 'Hybrid', 'No Stop'])
    axes[1, 0].set_ylabel('Return (%)')
    axes[1, 0].set_title('Return Distribution Box Plot')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].axhline(y=0, color='r', linestyle='--', alpha=0.5)
    
    # Plot 4: Percentile comparison
    percentiles = [10, 25, 50, 75, 90]
    fixed_pct = [np.percentile(fixed_returns, p) for p in percentiles]
    trailing_pct = [np.percentile(trailing_returns, p) for p in percentiles]
    hybrid_pct = [np.percentile(hybrid_returns, p) for p in percentiles]
    no_stop_pct = [np.percentile(no_stop_returns, p) for p in percentiles]
    
    x = np.arange(len(percentiles))
    width = 0.2
    
    axes[1, 1].bar(x - 1.5*width, fixed_pct, width, label='Fixed', alpha=0.8)
    axes[1, 1].bar(x - 0.5*width, trailing_pct, width, label='Trailing', alpha=0.8)
    axes[1, 1].bar(x + 0.5*width, hybrid_pct, width, label='Hybrid', alpha=0.8)
    axes[1, 1].bar(x + 1.5*width, no_stop_pct, width, label='No Stop', alpha=0.8)
    axes[1, 1].set_xlabel('Percentile')
    axes[1, 1].set_ylabel('Return (%)')
    axes[1, 1].set_title('Percentile Comparison')
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels([f'{p}th' for p in percentiles])
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig('trailing_stop_loss_comparison.png', dpi=300, bbox_inches='tight')
    print("\n[OK] Saved plot: trailing_stop_loss_comparison.png")
    
    return fig


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_report(biweekly_stats, weekly_stats, no_stop_stats, 
                   biweekly_risk, weekly_risk, no_stop_risk,
                   biweekly_stops, weekly_stops):
    """Generate comprehensive markdown report"""
    
    report = f"""# Weekly Stop Loss Backtesting Analysis Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Simulations**: {N_SIMULATIONS:,}  
**Initial Capital**: ${INITIAL_CAPITAL:,}  
**Testing Period**: {N_WEEKS} weeks (90 days)  
**Stop Loss**: {STOP_LOSS_PCT*100}%  
**Profit Target**: {PROFIT_TARGET*100}%

---

## Executive Summary

This analysis compares three approaches to managing a $1,000 portfolio over 90 days:

1. **Bi-Weekly Review**: Check positions every 2 weeks, apply stop loss at review points
2. **Weekly Review**: Check positions every week, apply stop loss at weekly checkpoints
3. **No Stop Loss**: Baseline comparison without downside protection

### Key Findings

| Metric | Bi-Weekly | Weekly | No Stop Loss | Winner |
|--------|-----------|--------|--------------|--------|
| Mean Return | {biweekly_stats['mean_return_pct']:.2f}% | {weekly_stats['mean_return_pct']:.2f}% | {no_stop_stats['mean_return_pct']:.2f}% | {'Weekly' if weekly_stats['mean_return_pct'] > biweekly_stats['mean_return_pct'] else 'Bi-Weekly'} |
| Median Return | {biweekly_stats['median_return_pct']:.2f}% | {weekly_stats['median_return_pct']:.2f}% | {no_stop_stats['median_return_pct']:.2f}% | {'Weekly' if weekly_stats['median_return_pct'] > biweekly_stats['median_return_pct'] else 'Bi-Weekly'} |
| Sharpe Ratio | {biweekly_risk['sharpe_ratio']:.3f} | {weekly_risk['sharpe_ratio']:.3f} | {no_stop_risk['sharpe_ratio']:.3f} | {'Weekly' if weekly_risk['sharpe_ratio'] > biweekly_risk['sharpe_ratio'] else 'Bi-Weekly'} |
| Max Drawdown | {biweekly_risk['max_drawdown_pct']:.2f}% | {weekly_risk['max_drawdown_pct']:.2f}% | {no_stop_risk['max_drawdown_pct']:.2f}% | {'Weekly' if abs(weekly_risk['max_drawdown_pct']) < abs(biweekly_risk['max_drawdown_pct']) else 'Bi-Weekly'} |
| P(Loss > 5%) | {biweekly_stats['probabilities']['below_minus5pct']:.2f}% | {weekly_stats['probabilities']['below_minus5pct']:.2f}% | {no_stop_stats['probabilities']['below_minus5pct']:.2f}% | {'Weekly' if weekly_stats['probabilities']['below_minus5pct'] < biweekly_stats['probabilities']['below_minus5pct'] else 'Bi-Weekly'} |

**Recommendation**: {'✅ **WEEKLY REVIEW** provides better risk-adjusted returns' if weekly_risk['sharpe_ratio'] > biweekly_risk['sharpe_ratio'] else '⚠️ **BI-WEEKLY REVIEW** may be sufficient'}

---

## Detailed Results

### 1. Bi-Weekly Review Approach

**Final Capital Statistics**:
- Mean: ${biweekly_stats['mean']:.2f} ({biweekly_stats['mean_return_pct']:+.2f}%)
- Median: ${biweekly_stats['median']:.2f} ({biweekly_stats['median_return_pct']:+.2f}%)
- Std Dev: ${biweekly_stats['std']:.2f} ({biweekly_stats['std_return_pct']:.2f}%)
- Range: ${biweekly_stats['min']:.2f} to ${biweekly_stats['max']:.2f}

**Percentile Analysis**:
- 10th percentile: ${biweekly_stats['percentiles']['10th']:.2f} ({(biweekly_stats['percentiles']['10th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)
- 25th percentile: ${biweekly_stats['percentiles']['25th']:.2f} ({(biweekly_stats['percentiles']['25th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)
- 50th percentile: ${biweekly_stats['percentiles']['50th']:.2f} ({(biweekly_stats['percentiles']['50th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)
- 75th percentile: ${biweekly_stats['percentiles']['75th']:.2f} ({(biweekly_stats['percentiles']['75th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)
- 90th percentile: ${biweekly_stats['percentiles']['90th']:.2f} ({(biweekly_stats['percentiles']['90th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)

**Probability Analysis**:
- P(Return > 0%): {biweekly_stats['probabilities']['positive']:.1f}%
- P(Return > 5%): {biweekly_stats['probabilities']['above_5pct']:.1f}%
- P(Return > 10%): {biweekly_stats['probabilities']['above_10pct']:.1f}%
- P(Return > 15%): {biweekly_stats['probabilities']['above_15pct']:.1f}%
- P(Return > 20%): {biweekly_stats['probabilities']['above_20pct']:.1f}%

**Risk Metrics**:
- Sharpe Ratio: {biweekly_risk['sharpe_ratio']:.3f}
- Sortino Ratio: {biweekly_risk['sortino_ratio']:.3f}
- Maximum Drawdown: {biweekly_risk['max_drawdown_pct']:.2f}%
- 95% VaR: {biweekly_risk['var_95_pct']:.2f}%

**Stop Loss Activity**:
- Average stops per simulation: {biweekly_stops.mean():.2f}
- Max stops in single simulation: {biweekly_stops.max():.0f}
- Simulations with no stops: {np.sum(biweekly_stops == 0)/len(biweekly_stops)*100:.1f}%

---

### 2. Weekly Review Approach (NEW)

**Final Capital Statistics**:
- Mean: ${weekly_stats['mean']:.2f} ({weekly_stats['mean_return_pct']:+.2f}%)
- Median: ${weekly_stats['median']:.2f} ({weekly_stats['median_return_pct']:+.2f}%)
- Std Dev: ${weekly_stats['std']:.2f} ({weekly_stats['std_return_pct']:.2f}%)
- Range: ${weekly_stats['min']:.2f} to ${weekly_stats['max']:.2f}

**Percentile Analysis**:
- 10th percentile: ${weekly_stats['percentiles']['10th']:.2f} ({(weekly_stats['percentiles']['10th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)
- 25th percentile: ${weekly_stats['percentiles']['25th']:.2f} ({(weekly_stats['percentiles']['25th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)
- 50th percentile: ${weekly_stats['percentiles']['50th']:.2f} ({(weekly_stats['percentiles']['50th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)
- 75th percentile: ${weekly_stats['percentiles']['75th']:.2f} ({(weekly_stats['percentiles']['75th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)
- 90th percentile: ${weekly_stats['percentiles']['90th']:.2f} ({(weekly_stats['percentiles']['90th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%)

**Probability Analysis**:
- P(Return > 0%): {weekly_stats['probabilities']['positive']:.1f}%
- P(Return > 5%): {weekly_stats['probabilities']['above_5pct']:.1f}%
- P(Return > 10%): {weekly_stats['probabilities']['above_10pct']:.1f}%
- P(Return > 15%): {weekly_stats['probabilities']['above_15pct']:.1f}%
- P(Return > 20%): {weekly_stats['probabilities']['above_20pct']:.1f}%

**Risk Metrics**:
- Sharpe Ratio: {weekly_risk['sharpe_ratio']:.3f}
- Sortino Ratio: {weekly_risk['sortino_ratio']:.3f}
- Maximum Drawdown: {weekly_risk['max_drawdown_pct']:.2f}%
- 95% VaR: {weekly_risk['var_95_pct']:.2f}%

**Stop Loss Activity**:
- Average stops per simulation: {weekly_stops.mean():.2f}
- Max stops in single simulation: {weekly_stops.max():.0f}
- Simulations with no stops: {np.sum(weekly_stops == 0)/len(weekly_stops)*100:.1f}%

---

### 3. No Stop Loss (Baseline)

**Final Capital Statistics**:
- Mean: ${no_stop_stats['mean']:.2f} ({no_stop_stats['mean_return_pct']:+.2f}%)
- Median: ${no_stop_stats['median']:.2f} ({no_stop_stats['median_return_pct']:+.2f}%)
- Std Dev: ${no_stop_stats['std']:.2f} ({no_stop_stats['std_return_pct']:.2f}%)
- Range: ${no_stop_stats['min']:.2f} to ${no_stop_stats['max']:.2f}

**Risk Metrics**:
- Sharpe Ratio: {no_stop_risk['sharpe_ratio']:.3f}
- Sortino Ratio: {no_stop_risk['sortino_ratio']:.3f}
- Maximum Drawdown: {no_stop_risk['max_drawdown_pct']:.2f}%
- 95% VaR: {no_stop_risk['var_95_pct']:.2f}%

---

## Comparative Analysis

### Return Comparison

| Scenario | Mean Return | Median Return | Difference from Bi-Weekly |
|----------|-------------|---------------|---------------------------|
| Bi-Weekly | {biweekly_stats['mean_return_pct']:.2f}% | {biweekly_stats['median_return_pct']:.2f}% | Baseline |
| Weekly | {weekly_stats['mean_return_pct']:.2f}% | {weekly_stats['median_return_pct']:.2f}% | {weekly_stats['mean_return_pct'] - biweekly_stats['mean_return_pct']:+.2f}% |
| No Stop Loss | {no_stop_stats['mean_return_pct']:.2f}% | {no_stop_stats['median_return_pct']:.2f}% | {no_stop_stats['mean_return_pct'] - biweekly_stats['mean_return_pct']:+.2f}% |

### Risk Comparison

| Metric | Bi-Weekly | Weekly | No Stop Loss | Best |
|--------|-----------|--------|--------------|------|
| Sharpe Ratio | {biweekly_risk['sharpe_ratio']:.3f} | {weekly_risk['sharpe_ratio']:.3f} | {no_stop_risk['sharpe_ratio']:.3f} | {'Weekly' if weekly_risk['sharpe_ratio'] == max(biweekly_risk['sharpe_ratio'], weekly_risk['sharpe_ratio'], no_stop_risk['sharpe_ratio']) else 'Bi-Weekly' if biweekly_risk['sharpe_ratio'] == max(biweekly_risk['sharpe_ratio'], weekly_risk['sharpe_ratio'], no_stop_risk['sharpe_ratio']) else 'No Stop'} |
| Sortino Ratio | {biweekly_risk['sortino_ratio']:.3f} | {weekly_risk['sortino_ratio']:.3f} | {no_stop_risk['sortino_ratio']:.3f} | {'Weekly' if weekly_risk['sortino_ratio'] == max(biweekly_risk['sortino_ratio'], weekly_risk['sortino_ratio'], no_stop_risk['sortino_ratio']) else 'Bi-Weekly' if biweekly_risk['sortino_ratio'] == max(biweekly_risk['sortino_ratio'], weekly_risk['sortino_ratio'], no_stop_risk['sortino_ratio']) else 'No Stop'} |
| Max Drawdown | {biweekly_risk['max_drawdown_pct']:.2f}% | {weekly_risk['max_drawdown_pct']:.2f}% | {no_stop_risk['max_drawdown_pct']:.2f}% | {'Weekly' if abs(weekly_risk['max_drawdown_pct']) == min(abs(biweekly_risk['max_drawdown_pct']), abs(weekly_risk['max_drawdown_pct']), abs(no_stop_risk['max_drawdown_pct'])) else 'Bi-Weekly' if abs(biweekly_risk['max_drawdown_pct']) == min(abs(biweekly_risk['max_drawdown_pct']), abs(weekly_risk['max_drawdown_pct']), abs(no_stop_risk['max_drawdown_pct'])) else 'No Stop'} |
| 95% VaR | {biweekly_risk['var_95_pct']:.2f}% | {weekly_risk['var_95_pct']:.2f}% | {no_stop_risk['var_95_pct']:.2f}% | {'Weekly' if abs(weekly_risk['var_95_pct']) == min(abs(biweekly_risk['var_95_pct']), abs(weekly_risk['var_95_pct']), abs(no_stop_risk['var_95_pct'])) else 'Bi-Weekly' if abs(biweekly_risk['var_95_pct']) == min(abs(biweekly_risk['var_95_pct']), abs(weekly_risk['var_95_pct']), abs(no_stop_risk['var_95_pct'])) else 'No Stop'} |

### Downside Protection

| Scenario | P(Loss) | P(Loss > 5%) | P(Loss > 10%) |
|----------|---------|--------------|---------------|
| Bi-Weekly | {biweekly_stats['probabilities']['below_0pct']:.2f}% | {biweekly_stats['probabilities']['below_minus5pct']:.2f}% | {biweekly_stats['probabilities']['below_minus10pct']:.2f}% |
| Weekly | {weekly_stats['probabilities']['below_0pct']:.2f}% | {weekly_stats['probabilities']['below_minus5pct']:.2f}% | {weekly_stats['probabilities']['below_minus10pct']:.2f}% |
| No Stop Loss | {no_stop_stats['probabilities']['below_0pct']:.2f}% | {no_stop_stats['probabilities']['below_minus5pct']:.2f}% | {no_stop_stats['probabilities']['below_minus10pct']:.2f}% |

---

## Recommendations

### Primary Recommendation

"""

    # Add recommendation based on results
    if weekly_risk['sharpe_ratio'] > biweekly_risk['sharpe_ratio'] * 1.05:
        report += """**✅ ADOPT WEEKLY REVIEW CYCLE**

The weekly review approach provides:
- Better risk-adjusted returns (higher Sharpe ratio)
- More frequent downside protection
- Earlier detection of losing positions
- More opportunities to rebalance

**Implementation**:
1. Review portfolio every Monday morning
2. Check each position against 2% stop loss threshold
3. Execute sells for positions triggering stop loss
4. Identify replacement candidates from approved universe
5. Execute buys same day

**Expected Improvement**:
- Sharpe Ratio: {:.1f}% better than bi-weekly
- Downside Protection: {:.1f}% reduction in P(Loss > 5%)
""".format(
    (weekly_risk['sharpe_ratio'] - biweekly_risk['sharpe_ratio']) / biweekly_risk['sharpe_ratio'] * 100,
    (biweekly_stats['probabilities']['below_minus5pct'] - weekly_stats['probabilities']['below_minus5pct'])
)
    else:
        report += """**⚠️ BI-WEEKLY REVIEW MAY BE SUFFICIENT**

The analysis shows minimal difference between weekly and bi-weekly reviews:
- Similar risk-adjusted returns
- Comparable downside protection
- Less frequent trading (lower effort)

**Recommendation**: Stick with bi-weekly review unless you prefer more active management.

**Trade-off**:
- Weekly: More protection, more effort
- Bi-Weekly: Similar results, less effort
"""

    report += """
### Alternative Approaches

1. **Hybrid Approach**: Weekly monitoring with bi-weekly rebalancing
   - Check stop losses weekly
   - Only rebalance full portfolio every 2 weeks
   - Best of both worlds

2. **Alert-Based**: Set price alerts at -2% threshold
   - Manual intervention only when needed
   - Reduces monitoring burden
   - Maintains downside protection

3. **Adaptive Frequency**: Adjust based on market volatility
   - Weekly reviews during high volatility
   - Bi-weekly during stable periods

---

## Conclusion

Based on {N_SIMULATIONS:,} Monte Carlo simulations:

**Expected 90-Day Outcome (Weekly Review)**:
- Most Likely: ${weekly_stats['median']:.2f} ({weekly_stats['median_return_pct']:+.2f}% return)
- Conservative (25th percentile): ${weekly_stats['percentiles']['25th']:.2f} ({(weekly_stats['percentiles']['25th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}% return)
- Optimistic (75th percentile): ${weekly_stats['percentiles']['75th']:.2f} ({(weekly_stats['percentiles']['75th']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}% return)

**Risk Profile**:
- Probability of profit: {weekly_stats['probabilities']['positive']:.1f}%
- Probability of >10% return: {weekly_stats['probabilities']['above_10pct']:.1f}%
- Probability of >5% loss: {weekly_stats['probabilities']['below_minus5pct']:.1f}%

**Stop Loss Effectiveness**:
- Average {weekly_stops.mean():.1f} stop loss triggers per 90-day period
- Limits maximum loss to approximately {weekly_risk['max_drawdown_pct']:.1f}%
- Provides {(no_stop_stats['probabilities']['below_minus5pct'] - weekly_stats['probabilities']['below_minus5pct']):.1f}% reduction in severe loss probability

---

## Appendix: Methodology

**Simulation Parameters**:
- Initial Capital: ${INITIAL_CAPITAL:,}
- Testing Period: {N_WEEKS} weeks
- Mean Weekly Return: {MEAN_WEEKLY_RETURN*100:.2f}%
- Weekly Volatility: {STD_WEEKLY_RETURN*100:.2f}%
- Stop Loss: {STOP_LOSS_PCT*100}%
- Profit Target: {PROFIT_TARGET*100}%
- Simulations: {N_SIMULATIONS:,}

**Data Source**: Empirical parameters from time_series_analyzer backtesting (AAPL, MSFT, NVDA, IBM)

**Assumptions**:
1. Returns follow normal distribution (validated by Central Limit Theorem)
2. Weekly returns are independent
3. Stop loss executed at exact threshold (no slippage in simulation)
4. Profit target caps upside at 3% per week
5. Transaction costs included in mean return calculation

**Limitations**:
1. Simplified model (actual markets more complex)
2. No consideration of individual stock selection
3. Assumes consistent execution
4. Does not model market regime changes

---

**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Script**: weekly_stop_loss_backtest.py  
**Author**: B. I. Parker Data Science and Consulting LLC
"""

    return report


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
    print(f"\n{i+1}. Determining optimal trailing stop level...")
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
    
    # Save results
    print(f"\n{i+2}. Saving results...")
    report_filename = 'TRAILING_STOP_ANALYSIS.md'
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"[OK] Saved report: {report_filename}")
    
    # Save results to JSON
    results_data = {
        'simulation_parameters': {
            'initial_capital': INITIAL_CAPITAL,
            'n_weeks': N_WEEKS,
            'mean_weekly_return': MEAN_WEEKLY_RETURN,
            'std_weekly_return': STD_WEEKLY_RETURN,
            'stop_loss_pct': STOP_LOSS_PCT,
            'profit_target': PROFIT_TARGET,
            'n_simulations': N_SIMULATIONS,
        },
        'biweekly_review': {
            'statistics': biweekly_stats,
            'risk_metrics': biweekly_risk,
            'stop_loss_triggers': {
                'mean': float(biweekly_stops.mean()),
                'max': int(biweekly_stops.max()),
                'pct_no_stops': float(np.sum(biweekly_stops == 0) / len(biweekly_stops) * 100)
            }
        },
        'weekly_review': {
            'statistics': weekly_stats,
            'risk_metrics': weekly_risk,
            'stop_loss_triggers': {
                'mean': float(weekly_stops.mean()),
                'max': int(weekly_stops.max()),
                'pct_no_stops': float(np.sum(weekly_stops == 0) / len(weekly_stops) * 100)
            }
        },
        'no_stop_loss': {
            'statistics': no_stop_stats,
            'risk_metrics': no_stop_risk,
        }
    }
    
    json_filename = 'weekly_stop_loss_results.json'
    with open(json_filename, 'w') as f:
        json.dump(results_data, f, indent=2)
    print(f"[OK] Saved results: {json_filename}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nBi-Weekly Review:")
    print(f"  Mean Return: {biweekly_stats['mean_return_pct']:+.2f}%")
    print(f"  Sharpe Ratio: {biweekly_risk['sharpe_ratio']:.3f}")
    print(f"  P(Profit): {biweekly_stats['probabilities']['positive']:.1f}%")
    
    print(f"\nWeekly Review:")
    print(f"  Mean Return: {weekly_stats['mean_return_pct']:+.2f}%")
    print(f"  Sharpe Ratio: {weekly_risk['sharpe_ratio']:.3f}")
    print(f"  P(Profit): {weekly_stats['probabilities']['positive']:.1f}%")
    
    print(f"\nNo Stop Loss:")
    print(f"  Mean Return: {no_stop_stats['mean_return_pct']:+.2f}%")
    print(f"  Sharpe Ratio: {no_stop_risk['sharpe_ratio']:.3f}")
    print(f"  P(Profit): {no_stop_stats['probabilities']['positive']:.1f}%")
    
    print("\n" + "=" * 70)
    print("Analysis complete! Check the following files:")
    print(f"  - {report_filename} (detailed report)")
    print(f"  - {json_filename} (raw results)")
    print(f"  - weekly_stop_loss_comparison.png (visualizations)")
    print("=" * 70)


if __name__ == "__main__":
    main()

# Made with Bob
