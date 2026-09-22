"""
Time Backstop Simulation
========================
For each trade, fetch daily closing prices and simulate:
  - Actual exit (as recorded)
  - ATR 2x trailing stop (from prior analysis)
  - Time backstop only: exit close of day 5 if position < +1%
  - ATR + Time backstop combined: first of ATR or day-5 check to fire

Threshold variants tested: 0% (breakeven), +0.5%, +1.0%

Output: time_backstop_results.json
"""

import json
import math
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

ATR_PERIOD     = 14
ATR_MULTIPLIER = 2.0
LOOKBACK       = 60
# Thresholds for "minimum progress" check on day 5
THRESHOLDS     = [0.00, 0.005, 0.01]   # 0%, 0.5%, 1.0%
BACKSTOP_DAY   = 5   # trading days after entry

# ── Trade pairs (same as prior analysis) ─────────────────────────────────────
TRADES = [
    dict(id='GILD',   ticker='GILD', shares=7,  buy_date='2026-06-08', buy_price=129.50,
         actual_pnl_total=-14.28,  atr_pnl_total=-45.43),
    dict(id='GOOG',   ticker='GOOG', shares=1,  buy_date='2026-06-08', buy_price=362.44,
         actual_pnl_total=-7.21,   atr_pnl_total=-11.91),
    dict(id='QCOM',   ticker='QCOM', shares=4,  buy_date='2026-06-09', buy_price=216.00,
         actual_pnl_total=-17.56,  atr_pnl_total=-17.12),
    dict(id='JNJ_1',  ticker='JNJ',  shares=3,  buy_date='2026-06-08', buy_price=232.77,
         actual_pnl_total=93.84,   atr_pnl_total=0.96),
    dict(id='MSFT',   ticker='MSFT', shares=2,  buy_date='2026-06-12', buy_price=388.18,
         actual_pnl_total=3.08,    atr_pnl_total=-25.50),
    dict(id='AAPL_1', ticker='AAPL', shares=1,  buy_date='2026-06-15', buy_price=294.01,
         actual_pnl_total=1.97,    atr_pnl_total=4.00),
    dict(id='META_1', ticker='META', shares=1,  buy_date='2026-06-17', buy_price=578.82,
         actual_pnl_total=-9.71,   atr_pnl_total=-1.60),
    dict(id='AAPL_2', ticker='AAPL', shares=1,  buy_date='2026-06-17', buy_price=298.69,
         actual_pnl_total=-2.31,   atr_pnl_total=-12.67),
    dict(id='META_2', ticker='META', shares=1,  buy_date='2026-07-02', buy_price=591.42,
         actual_pnl_total=-8.17,   atr_pnl_total=-4.32),
    dict(id='C',      ticker='C',    shares=5,  buy_date='2026-07-01', buy_price=139.81,
         actual_pnl_total=-11.80,  atr_pnl_total=-13.75),
    dict(id='JNJ_2',  ticker='JNJ',  shares=2,  buy_date='2026-07-13', buy_price=257.95,
         actual_pnl_total=-22.08,  atr_pnl_total=-9.82),
    dict(id='MU',     ticker='MU',   shares=1,  buy_date='2026-07-14', buy_price=969.34,
         actual_pnl_total=-10.15,  atr_pnl_total=-137.10),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_ohlcv(ticker, buy_date_str):
    buy_dt = datetime.strptime(buy_date_str, '%Y-%m-%d')
    start  = buy_dt - timedelta(days=ATR_PERIOD + LOOKBACK)
    end    = buy_dt + timedelta(days=90)
    df = yf.Ticker(ticker).history(start=start, end=end)
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def compute_atr(df):
    df = df.copy()
    df['prev_close'] = df['Close'].shift(1)
    df['tr'] = df.apply(lambda r: max(
        r['High'] - r['Low'],
        abs(r['High'] - r['prev_close']) if not math.isnan(r['prev_close']) else 0,
        abs(r['Low']  - r['prev_close']) if not math.isnan(r['prev_close']) else 0
    ), axis=1)
    df['atr14'] = df['tr'].rolling(ATR_PERIOD).mean()
    return df


def sim_time_backstop_only(sim_df, buy_price, threshold, backstop_day=BACKSTOP_DAY):
    """
    Exit at close of backstop_day if price < buy_price*(1+threshold).
    Otherwise hold until end of available data (proxy for ATR or other exit).
    Returns (exit_date, exit_price, reason, days_held)
    """
    trading_days = list(sim_df.iterrows())
    for i, (date, row) in enumerate(trading_days):
        day_num = i + 1   # day 1 = first day after purchase
        if day_num == backstop_day:
            close = float(row['Close'])
            if close < buy_price * (1 + threshold):
                return date.strftime('%Y-%m-%d'), round(close, 2), f'TIME_BACKSTOP_D{backstop_day}', day_num
    # Never triggered backstop — use last row
    last = trading_days[-1]
    return last[0].strftime('%Y-%m-%d'), round(float(last[1]['Close']), 2), 'HELD_TO_END', len(trading_days)


def sim_atr_with_backstop(sim_df, buy_price, atr_at_entry, threshold, backstop_day=BACKSTOP_DAY):
    """
    Whichever fires first:
      - ATR trailing stop: Low <= peak - 2*ATR
      - Time backstop: close of day N if price < buy_price*(1+threshold)
    """
    peak        = buy_price
    stop_floor  = peak - ATR_MULTIPLIER * atr_at_entry
    trading_days = list(sim_df.iterrows())

    for i, (date, row) in enumerate(trading_days):
        day_num = i + 1

        # Advance peak on High
        if row['High'] > peak:
            peak       = row['High']
            stop_floor = peak - ATR_MULTIPLIER * atr_at_entry

        # Check ATR stop (Low)
        if row['Low'] <= stop_floor:
            return date.strftime('%Y-%m-%d'), round(stop_floor, 2), 'ATR_STOP', day_num

        # Check time backstop at close of backstop_day
        if day_num == backstop_day:
            close = float(row['Close'])
            if close < buy_price * (1 + threshold):
                return date.strftime('%Y-%m-%d'), round(close, 2), f'TIME_BACKSTOP_D{backstop_day}', day_num

    last = trading_days[-1]
    return last[0].strftime('%Y-%m-%d'), round(float(last[1]['Close']), 2), 'HELD_TO_END', len(trading_days)


# ── Main ──────────────────────────────────────────────────────────────────────
print('=' * 70)
print('TIME BACKSTOP SIMULATION')
print('=' * 70)

all_results = []

for t in TRADES:
    print(f"\n{t['id']} ({t['ticker']})...")
    df      = fetch_ohlcv(t['ticker'], t['buy_date'])
    df      = compute_atr(df)
    buy_dt  = pd.Timestamp(t['buy_date']).normalize()

    # ATR at entry
    pre_buy      = df[df.index <= buy_dt].dropna(subset=['atr14'])
    atr_at_entry = float(pre_buy['atr14'].iloc[-1]) if not pre_buy.empty else 0.0

    # Simulation window: days AFTER purchase
    sim_df = df[df.index > buy_dt].copy()

    row_result = {
        'id'            : t['id'],
        'ticker'        : t['ticker'],
        'shares'        : t['shares'],
        'buy_date'      : t['buy_date'],
        'buy_price'     : t['buy_price'],
        'atr14_at_entry': round(atr_at_entry, 2),
        'atr_pct'       : round(atr_at_entry / t['buy_price'] * 100, 2),
        'actual_pnl'    : t['actual_pnl_total'],
        'atr_only_pnl'  : t['atr_pnl_total'],
        'backstop_variants': {}
    }

    for thresh in THRESHOLDS:
        label = f'thresh_{int(thresh*1000):03d}'   # e.g. thresh_000, thresh_005, thresh_010

        # ── Time backstop alone ──
        tb_date, tb_price, tb_reason, tb_days = sim_time_backstop_only(
            sim_df, t['buy_price'], thresh)
        tb_pnl = round((tb_price - t['buy_price']) * t['shares'], 2)

        # ── ATR + Time backstop ──
        comb_date, comb_price, comb_reason, comb_days = sim_atr_with_backstop(
            sim_df, t['buy_price'], atr_at_entry, thresh)
        comb_pnl = round((comb_price - t['buy_price']) * t['shares'], 2)

        row_result['backstop_variants'][label] = {
            'threshold_pct'    : thresh * 100,
            # time backstop alone
            'tb_exit_date'     : tb_date,
            'tb_exit_price'    : tb_price,
            'tb_reason'        : tb_reason,
            'tb_days_held'     : tb_days,
            'tb_pnl'           : tb_pnl,
            'tb_vs_actual'     : round(tb_pnl - t['actual_pnl_total'], 2),
            'tb_vs_atr'        : round(tb_pnl - t['atr_pnl_total'], 2),
            # ATR + time backstop combined
            'comb_exit_date'   : comb_date,
            'comb_exit_price'  : comb_price,
            'comb_reason'      : comb_reason,
            'comb_days_held'   : comb_days,
            'comb_pnl'         : comb_pnl,
            'comb_vs_actual'   : round(comb_pnl - t['actual_pnl_total'], 2),
            'comb_vs_atr'      : round(comb_pnl - t['atr_pnl_total'], 2),
        }

        print(f"  thresh={thresh*100:.1f}%  "
              f"TB-only: {tb_reason} day{tb_days} ${tb_price:.2f} P&L ${tb_pnl:+.2f}  |  "
              f"ATR+TB: {comb_reason} day{comb_days} ${comb_price:.2f} P&L ${comb_pnl:+.2f}")

    all_results.append(row_result)

# ── Totals ────────────────────────────────────────────────────────────────────
print('\n' + '=' * 70)
print('PORTFOLIO TOTALS')
print('=' * 70)

total_actual = sum(r['actual_pnl'] for r in all_results)
total_atr    = sum(r['atr_only_pnl'] for r in all_results)

print(f"\nActual total P&L : ${total_actual:+.2f}")
print(f"ATR-only total   : ${total_atr:+.2f}")

for thresh in THRESHOLDS:
    label = f'thresh_{int(thresh*1000):03d}'
    total_tb   = sum(r['backstop_variants'][label]['tb_pnl']   for r in all_results)
    total_comb = sum(r['backstop_variants'][label]['comb_pnl'] for r in all_results)
    print(f"\nThreshold {thresh*100:.1f}%:")
    print(f"  Time backstop alone   : ${total_tb:+.2f}  (vs actual: {total_tb - total_actual:+.2f})")
    print(f"  ATR + Time backstop   : ${total_comb:+.2f}  (vs actual: {total_comb - total_actual:+.2f}  |  vs ATR-only: {total_comb - total_atr:+.2f})")

# ── Save ──────────────────────────────────────────────────────────────────────
out = {
    'generated'     : datetime.now().isoformat(),
    'atr_multiplier': ATR_MULTIPLIER,
    'backstop_day'  : BACKSTOP_DAY,
    'thresholds'    : THRESHOLDS,
    'trades'        : all_results,
    'portfolio_totals': {
        'actual'   : round(total_actual, 2),
        'atr_only' : round(total_atr, 2),
    }
}
# add threshold totals
for thresh in THRESHOLDS:
    label = f'thresh_{int(thresh*1000):03d}'
    out['portfolio_totals'][f'tb_only_{label}']  = round(sum(r['backstop_variants'][label]['tb_pnl']   for r in all_results), 2)
    out['portfolio_totals'][f'comb_{label}']     = round(sum(r['backstop_variants'][label]['comb_pnl'] for r in all_results), 2)

with open('time_backstop_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print('\n[OK] Saved: time_backstop_results.json')
