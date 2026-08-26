# Weekly Stop Loss Backtesting Analysis Report

**Generated**: 2026-06-12 11:45:23  
**Simulations**: 10,000  
**Initial Capital**: $1,000  
**Testing Period**: 12 weeks (90 days)  
**Stop Loss**: 2.0%  
**Profit Target**: 3.0%

---

## Executive Summary

This analysis compares three approaches to managing a $1,000 portfolio over 90 days:

1. **Bi-Weekly Review**: Check positions every 2 weeks, apply stop loss at review points
2. **Weekly Review**: Check positions every week, apply stop loss at weekly checkpoints
3. **No Stop Loss**: Baseline comparison without downside protection

### Key Findings

| Metric | Bi-Weekly | Weekly | No Stop Loss | Winner |
|--------|-----------|--------|--------------|--------|
| Mean Return | 5.75% | 8.83% | 1.04% | Weekly |
| Median Return | 5.78% | 8.66% | 1.13% | Weekly |
| Sharpe Ratio | 0.314 | 0.622 | -0.269 | Weekly |
| Max Drawdown | -18.57% | nan% | -99.59% | Bi-Weekly |
| P(Loss > 5%) | 2.99% | 3.32% | 29.51% | Bi-Weekly |

**Recommendation**: ✅ **WEEKLY REVIEW** provides better risk-adjusted returns

---

## Detailed Results

### 1. Bi-Weekly Review Approach

**Final Capital Statistics**:
- Mean: $1057.51 (+5.75%)
- Median: $1057.78 (+5.78%)
- Std Dev: $55.74 (5.57%)
- Range: $885.84 to $1194.05

**Percentile Analysis**:
- 10th percentile: $983.66 (-1.63%)
- 25th percentile: $1020.00 (+2.00%)
- 50th percentile: $1057.78 (+5.78%)
- 75th percentile: $1095.52 (+9.55%)
- 90th percentile: $1132.82 (+13.28%)

**Probability Analysis**:
- P(Return > 0%): 84.0%
- P(Return > 5%): 54.9%
- P(Return > 10%): 22.6%
- P(Return > 15%): 4.6%
- P(Return > 20%): 0.0%

**Risk Metrics**:
- Sharpe Ratio: 0.314
- Sortino Ratio: 0.793
- Maximum Drawdown: -18.57%
- 95% VaR: -3.30%

**Stop Loss Activity**:
- Average stops per simulation: 1.56
- Max stops in single simulation: 6
- Simulations with no stops: 16.5%

---

### 2. Weekly Review Approach (NEW)

**Final Capital Statistics**:
- Mean: $1088.29 (+8.83%)
- Median: $1086.58 (+8.66%)
- Std Dev: $77.64 (7.76%)
- Range: $844.80 to $1372.31

**Percentile Analysis**:
- 10th percentile: $988.75 (-1.12%)
- 25th percentile: $1034.57 (+3.46%)
- 50th percentile: $1086.58 (+8.66%)
- 75th percentile: $1140.31 (+14.03%)
- 90th percentile: $1188.77 (+18.88%)

**Probability Analysis**:
- P(Return > 0%): 86.9%
- P(Return > 5%): 68.0%
- P(Return > 10%): 43.4%
- P(Return > 15%): 21.4%
- P(Return > 20%): 7.9%

**Risk Metrics**:
- Sharpe Ratio: 0.622
- Sortino Ratio: 1.720
- Maximum Drawdown: nan%
- 95% VaR: -3.62%

**Stop Loss Activity**:
- Average stops per simulation: 2.91
- Max stops in single simulation: 9
- Simulations with no stops: 3.6%

---

### 3. No Stop Loss (Baseline)

**Final Capital Statistics**:
- Mean: $1010.40 (+1.04%)
- Median: $1011.25 (+1.13%)
- Std Dev: $109.89 (10.99%)
- Range: $636.14 to $1379.58

**Risk Metrics**:
- Sharpe Ratio: -0.269
- Sortino Ratio: -0.466
- Maximum Drawdown: -99.59%
- 95% VaR: -16.90%

---

## Comparative Analysis

### Return Comparison

| Scenario | Mean Return | Median Return | Difference from Bi-Weekly |
|----------|-------------|---------------|---------------------------|
| Bi-Weekly | 5.75% | 5.78% | Baseline |
| Weekly | 8.83% | 8.66% | +3.08% |
| No Stop Loss | 1.04% | 1.13% | -4.71% |

### Risk Comparison

| Metric | Bi-Weekly | Weekly | No Stop Loss | Best |
|--------|-----------|--------|--------------|------|
| Sharpe Ratio | 0.314 | 0.622 | -0.269 | Weekly |
| Sortino Ratio | 0.793 | 1.720 | -0.466 | Weekly |
| Max Drawdown | -18.57% | nan% | -99.59% | Bi-Weekly |
| 95% VaR | -3.30% | -3.62% | -16.90% | Bi-Weekly |

### Downside Protection

| Scenario | P(Loss) | P(Loss > 5%) | P(Loss > 10%) |
|----------|---------|--------------|---------------|
| Bi-Weekly | 15.99% | 2.99% | 0.08% |
| Weekly | 13.06% | 3.32% | 0.40% |
| No Stop Loss | 45.97% | 29.51% | 16.38% |

---

## Recommendations

### Primary Recommendation

**✅ ADOPT WEEKLY REVIEW CYCLE**

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
- Sharpe Ratio: 98.0% better than bi-weekly
- Downside Protection: -0.3% reduction in P(Loss > 5%)

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
