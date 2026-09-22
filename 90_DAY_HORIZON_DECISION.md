# 90-Day Investment Horizon — Decision Document

**Prepared for**: B. I. Parker Data Science and Consulting LLC  
**Date**: 2026-09-10  
**Current Position**: C (Citigroup) — 3 shares @ $140.93, trailing stop pending  
**Portfolio Budget**: $2,500  
**Source Documents**: Six project artifacts consolidated below

---

## 1. What the 90-Day Horizon Actually Means for This System

The system was originally designed around a **90-day holding period** (`TRADING_SYSTEM_PLAN.md`, line 30), but the XGBoost forecaster only generates a **30–36 day forward forecast** (`config.py`: `FORECAST_DAYS = 30`). This creates a structural mismatch: the forecast horizon ends at day 36, but the intended hold extends to day 90. Days 37–90 are flying blind on signal.

This is the single most important constraint and should anchor the entire decision.

---

## 2. Pros vs Cons — Head-to-Head

| Factor | 90-Day Horizon | 30–36 Day Horizon | Source |
|--------|---------------|-------------------|--------|
| **XGBoost signal coverage** | Forecast expires at day 36 — days 37–90 have no model signal | Full coverage; exit within the forecast window | `config.py`, `TRADING_SYSTEM_PLAN.md` §2.2 |
| **XGBoost multi-step error** | Recursive error compounding amplifies past day ~15 (flat-line effect diagnosed on WFC) | Stays within the reliable forecast zone | `forecasting_methods.py` `predict()` |
| **Probability of profit** | **86.9%** over 12 weeks | Lower (shorter window = less time for trend to play out) | `WEEKLY_STOP_LOSS_ANALYSIS.md` |
| **Median return (90 days)** | **+8.66%** ($216 on $2,500) | Proportionally lower; ~3–4% on 30-day hold | `WEEKLY_STOP_LOSS_ANALYSIS.md` |
| **Annualized return at median** | +53.8% (geometric compounding) | ~45–50% annualized if rolled 12× per year | `ANNUALIZED_PERCENTILE_ANALYSIS.md` |
| **Transaction costs / friction** | Low — fewer entries/exits | Higher — 3× more round-trips per year on 30-day cycle | `90_DAY_TESTING_STATISTICAL_ANALYSIS.md` |
| **Stop-loss trigger frequency** | 2.91 triggers per 90-day period (weekly review) | ~1 trigger per 30-day period (similar rate, fewer total) | `WEEKLY_STOP_LOSS_ANALYSIS.md` |
| **Merrill GTC stop expiry** | **GTC orders expire in 60–90 days** — stop must be manually renewed mid-hold | Stop active for full hold; no renewal required | `MERRILL_LYNCH_TRADING_WORKFLOW.md` line 387 |
| **Sentiment report staleness** | Analyst reports > 90 days → FinBERT confidence auto-penalized ×0.8 | Sentiment remains fresh within 30-day window | `sentiment_engine.py` line 372 |
| **Backtest staleness** | Backtest older than 30 days should be reviewed if unusual price action | Backtest likely current | `mellea-trading-pipeline-operator-instructions.html` line 316 |
| **Capital efficiency** | Capital locked for 90 days — misses 2–3 rotation opportunities | Capital rotates 3× in 90 days, capturing more opportunities | `TRADING_SYSTEM_PLAN.md` §2.2 |
| **Compounding upside** | Gains compound within the single hold | Each rotation re-deploys gains immediately | `ANNUALIZED_PERCENTILE_ANALYSIS.md` |
| **Operational simplicity** | One order pair per position per quarter | Weekly rebalancing requires more active management | `MERRILL_LYNCH_TRADING_WORKFLOW.md` |
| **Downside containment** | Max drawdown capped at ~8% with stop-losses (95% confidence) | Same stop-loss protection; tighter time window = earlier exit | `90_DAY_TESTING_STATISTICAL_ANALYSIS.md` |

---

## 3. The Numbers — What the Backtests Show

### Monte Carlo Results (10,000 simulations, 90-day window, $1,000 starting capital)

All three review cadences were tested. **Weekly review** dominates:

| Review Cadence | Median Return | Sharpe Ratio | P(Profit) | P(Loss > 5%) | Avg Stop Triggers |
|----------------|--------------|--------------|-----------|--------------|-------------------|
| Weekly (7-day) | **+8.66%** | **0.622** | **86.9%** | 3.32% | 2.91 |
| Bi-Weekly (14-day) | +5.78% | 0.314 | 84.0% | 2.99% | 1.56 |
| No stop loss | +1.13% | -0.269 | — | 29.51% | 0 |

*Source: `WEEKLY_STOP_LOSS_ANALYSIS.md`*

### Percentile Outcomes on $2,500 Portfolio (90-day, weekly review)

| Percentile | Return | Profit on $2,500 | Annualized Return |
|------------|--------|------------------|-------------------|
| 10th (near-worst) | -1.12% | -$28 | -4.5% |
| 25th (conservative) | +3.46% | +$87 | +14.4% |
| 50th (median/likely) | +8.66% | +$217 | +39.2% |
| 75th (optimistic) | +14.03% | +$351 | +67.5% |
| 90th (best-case) | +18.88% | +$472 | +96.5% |

*Source: `WEEKLY_STOP_LOSS_ANALYSIS.md` + scaled to $2,500 from `ANNUALIZED_PERCENTILE_ANALYSIS.md`*

### Confidence Scenarios (9.4% expected value, empirically derived)

| Scenario | Confidence | Return Target | Dollar Profit | Monte Carlo Backing |
|----------|-----------|---------------|---------------|---------------------|
| Conservative | 70% | 6–9% | $150–225 | 73% probability of >5% |
| Moderate | 50% | 9–15% | $225–375 | 56% probability of >10% |
| Optimistic | 30% | 15–20% | $375–500 | 35% probability of >15% |

*Source: `90_DAY_TESTING_STATISTICAL_ANALYSIS.md`*

---

## 4. The Merrill Constraint — Critical Operational Risk

> *"Merrill Lynch GTC stop orders expire after 60–90 days. Verify all active trailing stops monthly and renew any that have lapsed."*  
> — `MERRILL_LYNCH_TRADING_WORKFLOW.md` line 387

**This is the most practical con of a 90-day hold.** If the stop expires at day 60 and is not renewed before day 61, the position is unprotected. Given the Merrill two-step rule (trailing stop placed the day *after* purchase), the operational calendar looks like:

```
Day 0:   Buy C @ $140.93
Day 1:   Place 5% trailing stop ($7.05 stop distance, trigger ~$133.88)
Day ~60: ⚠️ GTC stop order approaches expiry — must manually renew
Day 90:  Target exit or roll decision
```

**Action required**: Set a calendar reminder at purchase date for Day 55–58 to verify and renew the trailing stop before it lapses.

---

## 5. The XGBoost Signal Gap — Quantified

The pipeline's XGBoost forecast covers **30 trading days** forward. For C, bought on 2026-09-08:

```
Forecast valid through: ~2026-10-22 (30 trading days)
90-day hold would end:  ~2026-12-08
Signal gap:             ~34 trading days with no model guidance
```

During the signal gap (days 31–90), the only protection is the trailing stop. The pipeline's `daily_advisor` would be making hold/sell decisions based on **stale forecast data** unless the XGBoost model is re-run at day 30. The staleness check added to `find_forecast_json()` (5-day max age) means the pipeline *would* auto-trigger a fresh XGBoost run — but the known recursive mean-reversion bug (flat-line after ~day 15) means re-run forecasts beyond the first 15 steps are unreliable for price targets.

**Practical mitigation**: Re-run the XGBoost forecast at the 30-day mark and treat it as a fresh 30-day forecast window, effectively chaining two 30-day holds rather than a true 90-day hold.

---

## 6. Go/No-Go Thresholds (From `90_DAY_TESTING_STATISTICAL_ANALYSIS.md`)

Use these at each 30-day review checkpoint to decide whether to continue holding or exit:

| Grade | Criteria | Action |
|-------|----------|--------|
| **Proceed** | Return ≥ 5%, Win rate ≥ 55%, Max drawdown < 12%, MAPE < 5%, Sharpe > 0.5 | Hold through next 30-day window |
| **High Confidence** | Return ≥ 10%, Win rate ≥ 60%, Max drawdown < 10%, MAPE < 3%, Sharpe > 1.0 | Hold — consider adding to position |
| **Exit Review** | Return < 0% OR drawdown > 12% OR stop triggered | Exit or re-evaluate at next pipeline run |

---

## 7. Recommendation

**Use a chained 30-day structure, not a true 90-day hold.**

The 90-day holding period is a valid *target* but should be implemented as **three sequential 30-day review windows**, not a set-and-forget 90-day commitment. This captures all the statistical upside of the longer horizon while staying within the XGBoost model's reliable forecast range at each step.

| Decision Point | Action |
|----------------|--------|
| **Day 0** (today) | Hold C, place 5% trailing stop tomorrow |
| **Day 30** | Re-run XGBoost on C. If forecast still bullish and stop not triggered → hold. Otherwise → exit. |
| **Day 55–58** | Renew Merrill GTC trailing stop order before expiry |
| **Day 60** | Mid-hold review: assess drawdown vs Go/No-Go thresholds |
| **Day 90** | Full exit or third 30-day roll decision |

**For C specifically** (cost basis $140.93, 3 shares, 5% trailing stop):
- Trailing stop trigger: ~$133.88
- 90-day median expected profit: ~$217 on full $2,500 (if fully deployed), ~$37 on current 3-share position
- Downside protected: max loss ~$21.15 (3 × $7.05) if stop fires at worst time

---

## 8. Source Document Index

| Document | Relevance |
|----------|-----------|
| [`90_DAY_TESTING_STATISTICAL_ANALYSIS.md`](90_DAY_TESTING_STATISTICAL_ANALYSIS.md) | Primary Monte Carlo analysis, confidence scenarios, Go/No-Go thresholds |
| [`ANNUALIZED_PERCENTILE_ANALYSIS.md`](ANNUALIZED_PERCENTILE_ANALYSIS.md) | Geometric compounding of 90-day returns to annualized figures |
| [`WEEKLY_STOP_LOSS_ANALYSIS.md`](WEEKLY_STOP_LOSS_ANALYSIS.md) | Three-way comparison of review cadences; weekly review wins |
| [`MERRILL_LYNCH_TRADING_WORKFLOW.md`](MERRILL_LYNCH_TRADING_WORKFLOW.md) | GTC order expiry constraint (60–90 days); 90-day outlook section |
| [`TRADING_SYSTEM_PLAN.md`](TRADING_SYSTEM_PLAN.md) | Original 90-day design intent vs later pivot to 7–14 day optimization |
| [`XGBOOST_CANDIDATE_ANALYSIS_SUMMARY.md`](XGBOOST_CANDIDATE_ANALYSIS_SUMMARY.md) | 7–14 day vs 30–36 day hold recommendations by stock |

---

*Document prepared by B. I. Parker Data Science and Consulting LLC*  
*Last updated: 2026-09-10*
