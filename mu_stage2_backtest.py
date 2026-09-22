"""
Stage 2 - Trailing Stop Backtest for MU (Micron Technology)
Methodology: 3 years historical data, ATR-derived stop levels, Parkinson
             volatility estimator, 10,000 Monte Carlo sims.

MU is a high-volatility semiconductor stock — ATR% typically exceeds 5%.
High-vol rule applies: multiplier capped at 1×ATR, hard max 8%.
Time backstop: position closed if not >= +0.5% after 5 trading days.
"""
import math
import numpy as np
import pandas as pd
import yfinance as yf
import json
import sys
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

np.random.seed(42)

TICKER        = 'MU'
LOOKBACK_DAYS = 3 * 365
N_SIMS        = 10000
CAPITAL       = 650       # actual position size
HOLD_DAYS     = 252
ATR_PERIOD          = 14
ATR_MULTIPLIERS     = [1.0, 1.5, 2.0, 2.5, 3.0]
ATR_HIGHVOL_CAP_PCT = 5.0
ATR_HIGHVOL_MULT    = 1.0
MAX_STOP_PCT        = 0.08
BACKSTOP_DAYS       = 5
BACKSTOP_THRESHOLD  = 0.005

print('=' * 70)
print(f'STAGE 2 - TRAILING STOP BACKTEST: {TICKER}')
print(f'3yr data  |  7 stop levels  |  {N_SIMS:,} Monte Carlo simulations')
print('=' * 70)

# ── 1. Fetch data ─────────────────────────────────────────────────────────────
print(f'\n[1/4] Fetching 3 years of {TICKER} data...')
end   = datetime.now()
start = end - timedelta(days=LOOKBACK_DAYS + 30)
raw   = yf.Ticker(TICKER).history(start=start, end=end)
raw.index = pd.to_datetime(raw.index).tz_localize(None)

raw['park_var'] = (1.0 / (4.0 * math.log(2))) * (np.log(raw['High'] / raw['Low'])) ** 2
sigma = float(np.sqrt(raw['park_var'].mean()))

raw['ret'] = raw['Close'].pct_change()
raw = raw.dropna()
mu  = float(raw['ret'].mean())

raw['prev_close'] = raw['Close'].shift(1)
raw['tr'] = raw.apply(lambda r: max(
    r['High'] - r['Low'],
    abs(r['High'] - r['prev_close']) if not math.isnan(r['prev_close']) else 0,
    abs(r['Low']  - r['prev_close']) if not math.isnan(r['prev_close']) else 0
), axis=1)
raw['atr14'] = raw['tr'].rolling(ATR_PERIOD).mean()
raw = raw.dropna(subset=['atr14'])

current_price = float(raw['Close'].iloc[-1])
current_atr   = float(raw['atr14'].iloc[-1])
atr_pct       = current_atr / current_price

high_vol = atr_pct * 100 >= ATR_HIGHVOL_CAP_PCT
if high_vol:
    multipliers_to_test = [m for m in ATR_MULTIPLIERS if m <= ATR_HIGHVOL_MULT]
    if not multipliers_to_test:
        multipliers_to_test = [ATR_HIGHVOL_MULT]
else:
    multipliers_to_test = ATR_MULTIPLIERS

STOP_LEVELS = [min(m * atr_pct, MAX_STOP_PCT) for m in multipliers_to_test]

print(f'     Days fetched    : {len(raw)}')
print(f'     Price range     : ${raw["Close"].min():.2f} - ${raw["Close"].max():.2f}')
print(f'     Mean daily ret  : {mu*100:+.3f}%')
print(f'     Parkinson vol   : {sigma*100:.3f}%  (intraday High/Low estimator)')
print(f'     Current price   : ${current_price:.2f}')
print(f'     ATR(14)         : ${current_atr:.2f}  ({atr_pct*100:.2f}% of price)')
print(f'     High-vol stock  : {"YES — multiplier capped at 1×ATR" if high_vol else "NO"}')
print(f'     Stop levels     : {[f"{s*100:.2f}%" for s in STOP_LEVELS]}')
print(f'     Time backstop   : Day {BACKSTOP_DAYS}, threshold +{BACKSTOP_THRESHOLD*100:.1f}%')

# ── 2. Monte Carlo per stop level ─────────────────────────────────────────────
print(f'\n[2/4] Running {N_SIMS:,} simulations per stop level...')
results = {}

for mult, stop_pct in zip(multipliers_to_test, STOP_LEVELS):
    label  = f'{mult:.1f}×ATR ({stop_pct*100:.2f}%)'
    finals = []
    stops_list = []

    for _ in range(N_SIMS):
        cap   = CAPITAL
        peak  = CAPITAL
        stops = 0
        days_in_trade = 0
        for day in range(HOLD_DAYS):
            r    = np.random.normal(mu, sigma)
            cap *= (1 + r)
            days_in_trade += 1
            if cap > peak:
                peak = cap
            if (cap - peak) / peak <= -stop_pct:
                cap   = CAPITAL
                peak  = CAPITAL
                stops += 1
                days_in_trade = 0
                continue
            if days_in_trade == BACKSTOP_DAYS:
                if (cap - CAPITAL) / CAPITAL < BACKSTOP_THRESHOLD:
                    cap   = CAPITAL
                    peak  = CAPITAL
                    stops += 1
                    days_in_trade = 0
        finals.append(cap)
        stops_list.append(stops)

    finals     = np.array(finals)
    stops_arr  = np.array(stops_list)
    rets       = (finals - CAPITAL) / CAPITAL
    sharpe     = rets.mean() / rets.std() if rets.std() > 0 else 0

    results[label] = {
        'multiplier'    : mult,
        'stop_pct'      : round(stop_pct * 100, 4),
        'sharpe'        : round(sharpe, 4),
        'mean_ret_pct'  : round(rets.mean() * 100, 2),
        'median_ret_pct': round(float(np.median(rets)) * 100, 2),
        'p_loss_gt5'    : round(float((rets < -0.05).mean()) * 100, 2),
        'p_profit'      : round(float((rets > 0).mean()) * 100, 2),
        'avg_stops_yr'  : round(float(stops_arr.mean()), 1),
    }
    print(f'     {label} -> Sharpe {sharpe:.3f}  '
          f'Mean {rets.mean()*100:+.2f}%  '
          f'P(Loss>5%) {(rets<-0.05).mean()*100:.2f}%  '
          f'Stops/yr {stops_arr.mean():.1f}')

# ── 3. Find optimal ───────────────────────────────────────────────────────────
print('\n[3/4] Evaluating acceptance criteria...')
best_label  = None
best_sharpe = -999

for label, m in results.items():
    if m['sharpe'] > 0.3 and m['p_loss_gt5'] < 5.0:
        if m['sharpe'] > best_sharpe:
            best_sharpe = m['sharpe']
            best_label  = label

# ── 4. Report ─────────────────────────────────────────────────────────────────
print('\n[4/4] RESULTS')
print('=' * 70)
print(f'STAGE 2 BACKTESTING RESULTS -- {TICKER}')
print('=' * 70)
print(f'\n{"Stop Level":<24} {"Sharpe":<10} {"Mean Ret":<12} {"P(Loss>5%)":<14} '
      f'{"Stops/Yr":<10} {"P(Profit)":<10}')
print('-' * 70)
for label, m in results.items():
    mark = ' <-- RECOMMENDED' if label == best_label else ''
    print(f'{label:<24} {m["sharpe"]:<10.3f} {m["mean_ret_pct"]:>+9.2f}%  '
          f'{m["p_loss_gt5"]:>11.2f}%  {m["avg_stops_yr"]:>8.1f}   '
          f'{m["p_profit"]:>7.1f}%{mark}')
print('-' * 70)

passes = False
if best_label:
    bm = results[best_label]
    passes = bm['sharpe'] > 0.3 and bm['p_loss_gt5'] < 5.0
    print(f'\nRECOMMENDED TRAILING STOP : {best_label}')
    print(f'  Sharpe Ratio            : {bm["sharpe"]:.3f}')
    print(f'  Mean Annual Return      : {bm["mean_ret_pct"]:+.2f}%')
    print(f'  P(Loss > 5%)            : {bm["p_loss_gt5"]:.2f}%')
    print(f'  Expected Stops / Year   : {bm["avg_stops_yr"]}')
    print(f'  P(Profit)               : {bm["p_profit"]:.1f}%')
    print()
    if passes:
        print(f'[PASS] MU PASSES STAGE 2 -- proceed to Stage 3 (Sentiment Analysis)')
    else:
        print(f'[FAIL] MU FAILS STAGE 2 -- criteria not fully met')
else:
    print('\n[FAIL] No stop level meets Sharpe > 0.3 and P(Loss>5%) < 5%')
    print(f'[FAIL] MU FAILS STAGE 2')

print('=' * 70)

# Save
out = {
    'ticker'             : TICKER,
    'date'               : datetime.now().isoformat(),
    'methodology'        : 'ATR-based stops (Parkinson vol, High/Low trigger, time backstop)',
    'capital_used'       : CAPITAL,
    'daily_mu_pct'       : round(mu * 100, 4),
    'parkinson_sigma_pct': round(sigma * 100, 4),
    'current_price'      : round(current_price, 2),
    'atr14'              : round(current_atr, 4),
    'atr_pct_of_price'   : round(atr_pct * 100, 4),
    'high_vol_stock'     : high_vol,
    'backstop_days'      : BACKSTOP_DAYS,
    'backstop_threshold' : BACKSTOP_THRESHOLD,
    'recommended_stop'   : best_label,
    'stage2_pass'        : passes,
    'results'            : results,
}
with open('Analysis_Outcomes/MU_stage2_backtest.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f'\n[OK] Results saved to Analysis_Outcomes/MU_stage2_backtest.json')
