"""Fetch 3 years of daily OHLCV data from Yahoo Finance."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import LOOKBACK_YEARS


def fetch(ticker: str) -> tuple[pd.DataFrame, str]:
    """
    Fetch LOOKBACK_YEARS of daily data for ticker.

    Returns:
        (df, company_name)
        df columns: date, open, high, low, close, volume  (all lowercase)
    Raises:
        ValueError if no data returned.
    """
    end   = datetime.now()
    start = end - timedelta(days=int(LOOKBACK_YEARS * 365.25))

    print(f"\nFetching {LOOKBACK_YEARS}-year data for {ticker.upper()} "
          f"({start.date()} to {end.date()}) ...")

    t    = yf.Ticker(ticker)
    raw  = t.history(start=start, end=end)

    try:
        company_name = t.info.get('longName', ticker.upper())
    except Exception:
        company_name = ticker.upper()

    if raw.empty:
        raise ValueError(f"No data returned for {ticker}. Check ticker symbol.")

    df = raw.reset_index()
    df.columns = df.columns.str.lower()
    df.rename(columns={'date': 'date'}, inplace=True)

    # Keep only needed columns
    df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()

    # Coerce types, drop bad rows
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna().sort_values('date').reset_index(drop=True)

    # Strip timezone info from date column for consistency
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)

    print(f"  Fetched {len(df)} trading days  "
          f"({df['date'].iloc[0].date()} to {df['date'].iloc[-1].date()})")

    return df, company_name
