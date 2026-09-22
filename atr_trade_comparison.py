"""
ATR Trade Comparison — Merrill Edge vs. ATR-Based Trailing Stops
================================================================
Fetches historical OHLCV data for each traded stock, computes ATR(14)
at entry, simulates a 2×ATR trailing stop using daily High/Low, and
compares the outcome against what actually happened.

Matched trade pairs (from Merrill Edge export 08/04/2026):
  GILD   buy 7 @ $129.50  on 2026-06-08  →  sell 7 @ $127.46  on 2026-06-08 (stop-loss, same day cycle)
  GOOG   buy 1 @ $362.44  on 2026-06-08  →  sell 1 @ $355.23  on 2026-06-09
  QCOM   buy 4 @ $216.00  on 2026-06-09  →  sell 4 @ $211.61  on 2026-06-09 (stop, same cycle)
  JNJ_1  buy 3 @ $232.77  on 2026-06-08  →  sell 3 @ $264.05  on 2026-07-08
  MSFT   buy 2 @ $388.18  on 2026-06-12  →  sell 2 @ $389.72  on 2026-06-17
  AAPL_1 buy 1 @ $294.01  on 2026-06-15  →  sell 1 @ $295.98  on 2026-06-17
  META_1 buy 1 @ $578.82  on 2026-06-17  →  sell 1 @ $569.11  on 2026-06-17 (re-entry after stop)
  AAPL_2 buy 1 @ $298.69  on 2026-06-17  →  sell 1 @ $296.38  on 2026-06-23
  META_2 buy 1 @ $591.42  on 2026-07-02  →  sell 1 @ $583.25  on 2026-07-09
  C      buy 5 @ $139.81  on 2026-07-01  →  sell 5 @ $137.45  on 2026-07-08
  JNJ_2  buy 2 @ $257.95  on 2026-07-13  →  sell 2 @ $246.91  on 2026-07-15
  MU     buy 1 @ $969.34  on 2026-07-14  →  sell 1 @ $959.19  on 2026-07-24

Usage: python atr_trade_comparison.py
Output: atr_comparison_results.json
"""

import json
import sys
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

ATR_PERIOD      = 14
ATR_MULTIPLIER  = 2.0
LOOKBACK_BUFFER = 60   # extra days before entry to compute ATR(14)

# ── Trade pairs ───────────────────────────────────────────────────────────────
TRADES = [
    dict(id='GILD',   ticker='GILD',  shares=7,  buy_date='2026-06-08', buy_price=129.50,
         sell_date='2026-06-08', sell_price=127.46, actual_pnl_per_share=-2.04,
         note='Same-day stop-loss cycle (re-entry and exit same date)'),
    dict(id='GOOG',   ticker='GOOG',  shares=1,  buy_date='2026-06-08', buy_price=362.44,
         sell_date='2026-06-09', sell_price=355.23, actual_pnl_per_share=-7.21,
         note='Stop-loss next day'),
    dict(id='QCOM',   ticker='QCOM',  shares=4,  buy_date='2026-06-09', buy_price=216.00,
         sell_date='2026-06-09', sell_price=211.61, actual_pnl_per_share=-4.39,
         note='Same-day stop-loss cycle'),
    dict(id='JNJ_1',  ticker='JNJ',   shares=3,  buy_date='2026-06-08', buy_price=232.77,
         sell_date='2026-07-08', sell_price=264.05, actual_pnl_per_share=31.28,
         note='Stop-loss triggered positive exit (price rose then fell)'),
    dict(id='MSFT',   ticker='MSFT',  shares=2,  buy_date='2026-06-12', buy_price=388.18,
         sell_date='2026-06-17', sell_price=389.72, actual_pnl_per_share=1.54,
         note='Weekly exit, slight gain'),
    dict(id='AAPL_1', ticker='AAPL',  shares=1,  buy_date='2026-06-15', buy_price=294.01,
         sell_date='2026-06-17', sell_price=295.98, actual_pnl_per_share=1.97,
         note='Weekly exit, slight gain'),
    dict(id='META_1', ticker='META',  shares=1,  buy_date='2026-06-17', buy_price=578.82,
         sell_date='2026-06-17', sell_price=569.11, actual_pnl_per_share=-9.71,
         note='Same-day stop triggered; sold day of purchase'),
    dict(id='AAPL_2', ticker='AAPL',  shares=1,  buy_date='2026-06-17', buy_price=298.69,
         sell_date='2026-06-23', sell_price=296.38, actual_pnl_per_share=-2.31,
         note='Stop-loss triggered'),
    dict(id='META_2', ticker='META',  shares=1,  buy_date='2026-07-02', buy_price=591.42,
         sell_date='2026-07-09', sell_price=583.25, actual_pnl_per_share=-8.17,
         note='Stop-loss triggered'),
    dict(id='C',      ticker='C',     shares=5,  buy_date='2026-07-01', buy_price=139.81,
         sell_date='2026-07-08', sell_price=137.45, actual_pnl_per_share=-2.36,
         note='Stop-loss triggered'),
    dict(id='JNJ_2',  ticker='JNJ',   shares=2,  buy_date='2026-07-13', buy_price=257.95,
         sell_date='2026-07-15', sell_price=246.91, actual_pnl_per_share=-11.04,
         note='Stop-loss triggered 2 days after entry'),
    dict(id='MU',     ticker='MU',    shares=1,  buy_date='2026-07-14', buy_price=969.34,
         sell_date='2026-07-24', sell_price=959.19, actual_pnl_per_share=-10.15,
         note='Stop-loss triggered ~10 days after entry'),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_ohlcv(ticker, buy_date_str, sell_date_str):
    """Fetch OHLCV from ATR_PERIOD+LOOKBACK_BUFFER days before buy through sell+5."""
    buy_dt  = datetime.strptime(buy_date_str,  '%Y-%m-%d')
    sell_dt = datetime.strptime(sell_date_str, '%Y-%m-%d')
    start   = buy_dt  - timedelta(days=ATR_PERIOD + LOOKBACK_BUFFER)
    end     = sell_dt + timedelta(days=5)
    df = yf.Ticker(ticker).history(start=start, end=end)
    # Strip timezone so comparisons with naive Timestamps work
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def compute_atr(df, period=ATR_PERIOD):
    """Add TR and ATR columns to dataframe."""
    df = df.copy()
    df['prev_close'] = df['Close'].shift(1)
    df['tr'] = df.apply(lambda r: max(
        r['High'] - r['Low'],
        abs(r['High'] - r['prev_close']) if not math.isnan(r['prev_close']) else 0,
        abs(r['Low']  - r['prev_close']) if not math.isnan(r['prev_close']) else 0
    ), axis=1)
    df['atr14'] = df['tr'].rolling(period).mean()
    return df


def simulate_atr_trailing_stop(df, buy_date_str, buy_price, multiplier=ATR_MULTIPLIER):
    """
    Simulate a trailing stop using:
      - Peak advances on daily High
      - Stop floor = peak - multiplier * ATR
      - Trigger fires when daily Low <= stop floor
    Returns: (exit_date, exit_price, atr_at_entry, initial_stop_floor, peak_at_exit)
    """
    buy_dt = pd.Timestamp(buy_date_str).normalize()

    # Find ATR on or just before buy date
    pre_buy = df[df.index <= buy_dt].dropna(subset=['atr14'])
    if pre_buy.empty:
        return None
    atr_at_entry  = float(pre_buy['atr14'].iloc[-1])
    stop_distance = multiplier * atr_at_entry

    # Simulation starts the day AFTER buy (trailing stop placed next day, per 24hr rule)
    sim_df = df[df.index > buy_dt].copy()
    if sim_df.empty:
        return None

    peak       = buy_price
    stop_floor = peak - stop_distance

    for date, row in sim_df.iterrows():
        # Advance peak on today's High
        if row['High'] > peak:
            peak       = row['High']
            stop_floor = peak - stop_distance   # ATR distance is fixed from entry ATR

        # Trigger if Low touches or crosses stop floor
        if row['Low'] <= stop_floor:
            exit_date  = date.strftime('%Y-%m-%d')
            exit_price = round(stop_floor, 2)
            return dict(
                exit_date        = exit_date,
                exit_price       = exit_price,
                atr_at_entry     = round(atr_at_entry, 4),
                atr_pct_of_price = round(atr_at_entry / buy_price * 100, 2),
                stop_distance_pct= round(stop_distance / buy_price * 100, 2),
                initial_stop     = round(buy_price - stop_distance, 2),
                peak_at_exit     = round(peak, 2),
                triggered        = True,
            )

    # Never triggered — use last available date and price
    last_row  = sim_df.iloc[-1]
    return dict(
        exit_date        = last_row.name.strftime('%Y-%m-%d'),
        exit_price       = round(float(last_row['Close']), 2),
        atr_at_entry     = round(atr_at_entry, 4),
        atr_pct_of_price = round(atr_at_entry / buy_price * 100, 2),
        stop_distance_pct= round(stop_distance / buy_price * 100, 2),
        initial_stop     = round(buy_price - stop_distance, 2),
        peak_at_exit     = round(float(sim_df['High'].max()), 2),
        triggered        = False,
    )


# ── Main ──────────────────────────────────────────────────────────────────────
print('=' * 70)
print('ATR TRADE COMPARISON — MERRILL EDGE ACTUAL vs. 2×ATR SIMULATION')
print('=' * 70)

results = []

for t in TRADES:
    print(f"\nProcessing {t['id']} ({t['ticker']})...")
    try:
        df  = fetch_ohlcv(t['ticker'], t['buy_date'], t['sell_date'])
        df  = compute_atr(df)
        atr_sim = simulate_atr_trailing_stop(df, t['buy_date'], t['buy_price'])

        if atr_sim is None:
            print(f"  [WARN] Could not compute ATR for {t['id']}")
            continue

        actual_pnl_total = round(t['actual_pnl_per_share'] * t['shares'], 2)
        atr_pnl_per_share = round(atr_sim['exit_price'] - t['buy_price'], 2)
        atr_pnl_total     = round(atr_pnl_per_share * t['shares'], 2)
        improvement       = round(atr_pnl_total - actual_pnl_total, 2)

        actual_pnl_pct = round(t['actual_pnl_per_share'] / t['buy_price'] * 100, 2)
        atr_pnl_pct    = round(atr_pnl_per_share / t['buy_price'] * 100, 2)

        # Days held
        buy_dt  = datetime.strptime(t['buy_date'],  '%Y-%m-%d')
        sell_dt = datetime.strptime(t['sell_date'],  '%Y-%m-%d')
        atr_dt  = datetime.strptime(atr_sim['exit_date'], '%Y-%m-%d')
        actual_days_held = (sell_dt - buy_dt).days
        atr_days_held    = (atr_dt  - buy_dt).days

        record = {
            'id'               : t['id'],
            'ticker'           : t['ticker'],
            'shares'           : t['shares'],
            'buy_date'         : t['buy_date'],
            'buy_price'        : t['buy_price'],
            # Actual
            'actual_sell_date' : t['sell_date'],
            'actual_sell_price': t['buy_price'] + t['actual_pnl_per_share'],
            'actual_pnl_per_sh': t['actual_pnl_per_share'],
            'actual_pnl_total' : actual_pnl_total,
            'actual_pnl_pct'   : actual_pnl_pct,
            'actual_days_held' : actual_days_held,
            'actual_note'      : t['note'],
            # ATR simulation
            'atr_sell_date'    : atr_sim['exit_date'],
            'atr_sell_price'   : atr_sim['exit_price'],
            'atr_pnl_per_sh'   : atr_pnl_per_share,
            'atr_pnl_total'    : atr_pnl_total,
            'atr_pnl_pct'      : atr_pnl_pct,
            'atr_days_held'    : atr_days_held,
            'atr_triggered'    : atr_sim['triggered'],
            'atr14_at_entry'   : atr_sim['atr_at_entry'],
            'atr_pct_of_price' : atr_sim['atr_pct_of_price'],
            'stop_distance_pct': atr_sim['stop_distance_pct'],
            'initial_stop'     : atr_sim['initial_stop'],
            'peak_at_exit'     : atr_sim['peak_at_exit'],
            # Delta
            'improvement_total': improvement,
        }
        results.append(record)

        print(f"  Actual : sell {t['sell_date']} @ ${record['actual_sell_price']:.2f}  "
              f"P&L ${actual_pnl_total:+.2f}  ({actual_pnl_pct:+.2f}%)")
        print(f"  ATR 2x : sell {atr_sim['exit_date']} @ ${atr_sim['exit_price']:.2f}  "
              f"P&L ${atr_pnl_total:+.2f}  ({atr_pnl_pct:+.2f}%)  "
              f"ATR={atr_sim['atr_pct_of_price']:.2f}% stop={atr_sim['stop_distance_pct']:.2f}%")
        print(f"  Delta  : {'+' if improvement >= 0 else ''}{improvement:.2f}")

    except Exception as e:
        print(f"  [ERROR] {t['id']}: {e}")

# Summary
total_actual = sum(r['actual_pnl_total'] for r in results)
total_atr    = sum(r['atr_pnl_total']    for r in results)
total_improv = round(total_atr - total_actual, 2)

print('\n' + '=' * 70)
print(f'TOTAL ACTUAL P&L  : ${total_actual:+.2f}')
print(f'TOTAL ATR P&L     : ${total_atr:+.2f}')
print(f'NET IMPROVEMENT   : ${total_improv:+.2f}')
print('=' * 70)

# Save
out = {
    'generated'       : datetime.now().isoformat(),
    'atr_period'      : ATR_PERIOD,
    'atr_multiplier'  : ATR_MULTIPLIER,
    'trades'          : results,
    'summary'         : {
        'total_actual_pnl' : round(total_actual, 2),
        'total_atr_pnl'    : round(total_atr, 2),
        'net_improvement'  : total_improv,
        'n_trades'         : len(results),
    }
}
with open('atr_comparison_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print('\n[OK] Results saved to stock-trading-system/atr_comparison_results.json')
