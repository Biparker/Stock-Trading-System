"""Feature engineering for Time Series B.

All features are computed from OHLCV data and expressed as returns or
normalised indicators so the model learns patterns, not price levels.

Features produced per row
──────────────────────────
  ret_1d … ret_30d        : 1/2/3/5/10/20/30-day close-to-close log returns
  rsi_14                  : RSI(14) scaled 0-1
  macd_line               : MACD line  (normalised by close)
  macd_signal             : MACD signal (normalised by close)
  macd_hist               : MACD histogram (normalised by close)
  bb_pos                  : (close - lower_band) / (upper_band - lower_band)
  bb_width                : (upper - lower) / middle  (bandwidth)
  vol_ratio               : today's volume / 20-day avg volume
  atr_pct                 : 14-day ATR / close  (volatility proxy)

Target (y)
───────────
  fwd_ret_30d  : 30-trading-day forward log return (%)
                 = log(close[t+30] / close[t]) * 100
"""

import numpy as np
import pandas as pd
from config import LAG_DAYS, RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL, \
                   BB_PERIOD, BB_STD, VOL_MA_PERIOD, FORECAST_DAYS


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all feature columns and the forward-return target to df.

    Rows where any feature or target is NaN are dropped.
    Returns a copy -- original df is not modified.
    """
    d = df.copy()
    close  = d['close']
    high   = d['high']
    low    = d['low']
    volume = d['volume']

    # ── Lag return features ──────────────────────────────────────────────────
    for lag in LAG_DAYS:
        d[f'ret_{lag}d'] = np.log(close / close.shift(lag)) * 100

    # ── RSI ──────────────────────────────────────────────────────────────────
    delta  = close.diff()
    gain   = delta.clip(lower=0)
    loss   = (-delta).clip(lower=0)
    avg_g  = gain.ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()
    avg_l  = loss.ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()
    rs     = avg_g / avg_l.replace(0, np.nan)
    d['rsi_14'] = (100 - 100 / (1 + rs)) / 100   # scaled 0-1

    # ── MACD (normalised by close price) ────────────────────────────────────
    ema_fast   = close.ewm(span=MACD_FAST,   adjust=False).mean()
    ema_slow   = close.ewm(span=MACD_SLOW,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    macd_sig   = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    d['macd_line']   = macd_line  / close
    d['macd_signal'] = macd_sig   / close
    d['macd_hist']   = (macd_line - macd_sig) / close

    # ── Bollinger Bands ──────────────────────────────────────────────────────
    sma    = close.rolling(BB_PERIOD).mean()
    std    = close.rolling(BB_PERIOD).std()
    upper  = sma + BB_STD * std
    lower  = sma - BB_STD * std
    band_w = upper - lower
    d['bb_pos']   = (close - lower) / band_w.replace(0, np.nan)
    d['bb_width'] = band_w / sma

    # ── Volume ratio ─────────────────────────────────────────────────────────
    vol_ma = volume.rolling(VOL_MA_PERIOD).mean()
    d['vol_ratio'] = volume / vol_ma.replace(0, np.nan)

    # ── ATR % ────────────────────────────────────────────────────────────────
    prev_close  = close.shift(1)
    tr          = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs()
    ], axis=1).max(axis=1)
    d['atr_pct'] = tr.ewm(span=14, adjust=False).mean() / close

    # ── Forward return target (30 trading days) ──────────────────────────────
    d['fwd_ret_30d'] = np.log(close.shift(-FORECAST_DAYS) / close) * 100

    d = d.dropna().reset_index(drop=True)
    return d


FEATURE_COLS = (
    [f'ret_{l}d' for l in LAG_DAYS]
    + ['rsi_14', 'macd_line', 'macd_signal', 'macd_hist',
       'bb_pos', 'bb_width', 'vol_ratio', 'atr_pct']
)
TARGET_COL = 'fwd_ret_30d'
