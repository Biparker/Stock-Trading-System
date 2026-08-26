"""
Generic Stage 2 - ATR Trailing Stop Backtest
=============================================
Run Stage 2 for ANY ticker using ATR-based stops, Parkinson volatility,
and the Day-5 time backstop.

Usage:
    python stage2_backtest.py --ticker AAPL
    python stage2_backtest.py --ticker JNJ --capital 500

Stop levels are derived from ATR(14) multipliers, not fixed percentages.
High-vol rule: if ATR% of price >= 5%, multiplier is capped at 1×.
Hard cap: stop distance never exceeds 8% of entry price.
Time backstop: exit at Day-5 close if position not up >= +0.5%.
Acceptance criteria: Sharpe > 0.3 AND P(Loss > 5%) < 5.0%
"""
import argparse
import math
import json
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

np.random.seed(42)

# ── Defaults (overridable via CLI) ────────────────────────────────────────────
LOOKBACK_DAYS       = 3 * 365
N_SIMS              = 10000
CAPITAL             = 1000
HOLD_DAYS           = 252
ATR_PERIOD          = 14
ATR_MULTIPLIERS     = [1.0, 1.5, 2.0, 2.5, 3.0]
ATR_HIGHVOL_CAP_PCT = 5.0
ATR_HIGHVOL_MULT    = 1.0
MAX_STOP_PCT        = 0.08
BACKSTOP_DAYS       = 5
BACKSTOP_THRESHOLD  = 0.005   # +0.5%

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description='Stage 2 ATR backtest for any ticker')
parser.add_argument('--ticker',  required=True, help='Stock ticker, e.g. AAPL')
parser.add_argument('--capital', type=float, default=CAPITAL,
                    help=f'Position size in $ (default {CAPITAL})')
args   = parser.parse_args()
TICKER  = args.ticker.upper()
CAPITAL = args.capital

print('=' * 70)
print(f'STAGE 2 - ATR TRAILING STOP BACKTEST: {TICKER}')
print(f'3yr data  |  ATR-based stops  |  {N_SIMS:,} Monte Carlo simulations')
print('=' * 70)

# ── 1. Fetch data ─────────────────────────────────────────────────────────────
print(f'\n[1/4] Fetching 3 years of {TICKER} data...')
end   = datetime.now()
start = end - timedelta(days=LOOKBACK_DAYS + 30)
raw   = yf.Ticker(TICKER).history(start=start, end=end)
raw.index = pd.to_datetime(raw.index).tz_localize(None)

# Parkinson volatility (High/Low — more accurate than Close-only)
raw['park_var'] = (1.0 / (4.0 * math.log(2))) * (np.log(raw['High'] / raw['Low'])) ** 2
sigma = float(np.sqrt(raw['park_var'].mean()))

# Mean daily return from Close
raw['ret'] = raw['Close'].pct_change()
raw = raw.dropna()
mu  = float(raw['ret'].mean())

# ATR(14)
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
print(f'     Parkinson vol   : {sigma*100:.3f}%')
print(f'     Current price   : ${current_price:.2f}')
print(f'     ATR(14)         : ${current_atr:.2f}  ({atr_pct*100:.2f}% of price)')
print(f'     High-vol stock  : {"YES — multiplier capped at 1xATR" if high_vol else "NO"}')
print(f'     Stop levels     : {[f"{s*100:.2f}%" for s in STOP_LEVELS]}')
print(f'     Time backstop   : Day {BACKSTOP_DAYS}, threshold +{BACKSTOP_THRESHOLD*100:.1f}%')

# ── 2. Monte Carlo ────────────────────────────────────────────────────────────
print(f'\n[2/4] Running {N_SIMS:,} simulations per stop level...')
results = {}

for mult, stop_pct in zip(multipliers_to_test, STOP_LEVELS):
    label      = f'{mult:.1f}xATR ({stop_pct*100:.2f}%)'
    finals     = []
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

    finals    = np.array(finals)
    stops_arr = np.array(stops_list)
    rets      = (finals - CAPITAL) / CAPITAL
    sharpe    = rets.mean() / rets.std() if rets.std() > 0 else 0

    results[label] = {
        'multiplier'     : mult,
        'stop_pct'       : round(stop_pct * 100, 4),
        'sharpe'         : round(sharpe, 4),
        'mean_ret_pct'   : round(rets.mean() * 100, 2),
        'median_ret_pct' : round(float(np.median(rets)) * 100, 2),
        'p_loss_gt5'     : round(float((rets < -0.05).mean()) * 100, 2),
        'p_profit'       : round(float((rets > 0).mean()) * 100, 2),
        'avg_stops_yr'   : round(float(stops_arr.mean()), 1),
    }
    print(f'     {label} -> Sharpe {sharpe:.3f}  '
          f'Mean {rets.mean()*100:+.2f}%  '
          f'P(Loss>5%) {(rets<-0.05).mean()*100:.2f}%  '
          f'Stops/yr {stops_arr.mean():.1f}')

# ── 3. Find optimal ───────────────────────────────────────────────────────────
print('\n[3/4] Evaluating acceptance criteria...')
best_label, best_sharpe = None, -999
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
print(f'\n{"Stop Level":<26} {"Sharpe":<10} {"Mean Ret":<12} {"P(Loss>5%)":<14} '
      f'{"Stops/Yr":<10} {"P(Profit)":<10}')
print('-' * 70)
for label, m in results.items():
    mark = ' <-- RECOMMENDED' if label == best_label else ''
    print(f'{label:<26} {m["sharpe"]:<10.3f} {m["mean_ret_pct"]:>+9.2f}%  '
          f'{m["p_loss_gt5"]:>11.2f}%  {m["avg_stops_yr"]:>8.1f}   '
          f'{m["p_profit"]:>7.1f}%{mark}')
print('-' * 70)

passes = False
if best_label:
    bm     = results[best_label]
    passes = bm['sharpe'] > 0.3 and bm['p_loss_gt5'] < 5.0
    print(f'\nRECOMMENDED TRAILING STOP : {best_label}')
    print(f'  Sharpe Ratio            : {bm["sharpe"]:.3f}')
    print(f'  Mean Annual Return      : {bm["mean_ret_pct"]:+.2f}%')
    print(f'  P(Loss > 5%)            : {bm["p_loss_gt5"]:.2f}%')
    print(f'  Expected Stops / Year   : {bm["avg_stops_yr"]}')
    print(f'  P(Profit)               : {bm["p_profit"]:.1f}%')
    print()
    verdict = 'PASSES' if passes else 'FAILS'
    print(f'[{"PASS" if passes else "FAIL"}] {TICKER} {verdict} STAGE 2'
          + (' -- proceed to Stage 3 (Sentiment Analysis)' if passes else ''))
else:
    print(f'\n[FAIL] No stop level meets criteria — {TICKER} FAILS STAGE 2')
print('=' * 70)

# ── 5. Save outputs ───────────────────────────────────────────────────────────
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

import os
json_path = f'Analysis_Outcomes/{TICKER}_stage2_backtest.json'
os.makedirs('Analysis_Outcomes', exist_ok=True)
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(f'\n[OK] Results saved to {json_path}')

status   = 'passed' if passes else 'failed'
txt_path = f'Analysis_Outcomes/{TICKER}_stage2_{status}.txt'
with open(txt_path, 'w', encoding='utf-8') as f:
    f.write(f'{TICKER} - STAGE 2 {"PASSED" if passes else "FAILED"}\n')
    f.write(f'Date: {datetime.now().strftime("%Y-%m-%d")}\n')
    f.write(f'Decision: {"Proceed to Stage 3 (Sentiment Analysis)" if passes else "Do not proceed"}\n\n')
    f.write('METHODOLOGY (ATR-BASED STOPS):\n')
    f.write(f'- Data: 3 years of {TICKER} daily OHLCV history ({len(raw)} trading days)\n')
    f.write(f'- Price range: ${raw["Close"].min():.2f} - ${raw["Close"].max():.2f}\n')
    f.write(f'- Mean daily return: {mu*100:+.3f}%\n')
    f.write(f'- Parkinson volatility (High/Low): {sigma*100:.3f}%\n')
    f.write(f'- Current price: ${current_price:.2f}\n')
    f.write(f'- ATR(14): ${current_atr:.2f} ({atr_pct*100:.2f}% of price)\n')
    f.write(f'- High-vol treatment: {"YES" if high_vol else "NO"}\n')
    f.write(f'- Multipliers tested: {multipliers_to_test}\n')
    f.write(f'- Time backstop: Day {BACKSTOP_DAYS}, min gain +{BACKSTOP_THRESHOLD*100:.1f}%\n')
    f.write(f'- Simulations: {N_SIMS:,} per stop level\n\n')
    f.write(f'{"Stop Level":<26} {"Sharpe":<10} {"Mean Ret":<12} {"P(Loss>5%)":<14} {"Stops/Yr":<10} {"P(Profit)"}\n')
    for label, m in results.items():
        mark = '  <-- RECOMMENDED' if label == best_label else ''
        f.write(f'{label:<26} {m["sharpe"]:<10.3f} {m["mean_ret_pct"]:>+9.2f}%  '
                f'{m["p_loss_gt5"]:>11.2f}%  {m["avg_stops_yr"]:>8.1f}   '
                f'{m["p_profit"]:>7.1f}%{mark}\n')
    if best_label:
        bm = results[best_label]
        f.write(f'\nRECOMMENDED STOP: {best_label}\n')
        f.write(f'- Sharpe : {bm["sharpe"]:.3f}\n')
        f.write(f'- Mean Return: {bm["mean_ret_pct"]:+.2f}%\n')
        f.write(f'- P(Loss>5%): {bm["p_loss_gt5"]:.2f}%\n')
        f.write(f'- Stops/yr  : {bm["avg_stops_yr"]}\n\n')
        f.write(f'STAGE 2 DECISION: {"PASS" if passes else "FAIL"}\n')
        if passes:
            f.write('NEXT STEP: Stage 3 -- Sentiment Analysis\n')
            f.write(f'  Download Morningstar analyst report for {TICKER} from Merrill Lynch\n')
            f.write(f'  Save to: sentiment_analyzer/Analyst_reports/Analyst_{TICKER}.pdf\n')
            f.write(f'  Run: python main.py --ticker {TICKER} '
                    f'--pdf-path "Analyst_reports/Analyst_{TICKER}.pdf"\n')
print(f'[OK] Outcome saved to {txt_path}')

# Made with Bob
