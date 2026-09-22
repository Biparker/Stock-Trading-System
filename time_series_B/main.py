#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Time Series B -- XGBoost 30-Day Relative Return Forecaster
==========================================================
Stage 1 screening tool for the B.I. Parker trading system.

Key differences from time_series_analyzer (Method A):
  * Uses 3 years of data: years 1-2 train, year 3 out-of-sample validation
  * Predicts 30-day FORWARD RELATIVE RETURN (%), not an absolute price
  * Direct single-shot prediction -- no iterative chaining, no error compounding
  * Richer features: lag returns, RSI, MACD, Bollinger Bands, volume ratio, ATR

Usage:
    python main.py --ticker AAPL
    python main.py --ticker MSFT --threshold 3.0
    python main.py --ticker GOOGL --no-plots

Output (saved to time_series_B/output/):
    TICKER_tsB_report.json
    TICKER_tsB_report.txt
    plots/TICKER_tsB_forecast.png
"""

import argparse
import os
import sys

# Make local imports work when run from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as cfg


def parse_args():
    p = argparse.ArgumentParser(
        description='Time Series B -- XGBoost 30-day relative return forecast')
    p.add_argument('--ticker',    required=True,  type=str,   help='Stock ticker, e.g. AAPL')
    p.add_argument('--threshold', default=None,   type=float, help='Override MIN_FORECAST_RETURN (%%)')
    p.add_argument('--no-plots',  action='store_true',        help='Skip chart generation')
    return p.parse_args()


def run(ticker: str, threshold: float = None, make_plots: bool = True) -> dict:
    """
    Full pipeline for a single ticker.

    Returns the prediction dict (forecast_return_pct, signal, etc.)
    """
    import data_fetcher      as df_mod
    import feature_engineer  as fe_mod
    import xgboost_model     as xm_mod
    import report_generator  as rg_mod
    import visualizer        as viz_mod

    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    os.makedirs(cfg.PLOTS_DIR,  exist_ok=True)

    # Override threshold if supplied via CLI
    if threshold is not None:
        cfg.MIN_FORECAST_RETURN = threshold

    ticker = ticker.upper()
    print("\n" + "=" * 70)
    print(f"TIME SERIES B -- {ticker}")
    print("=" * 70)

    # ── 1. Fetch data ─────────────────────────────────────────────────────────
    print("\n[1/5] Fetching 3-year OHLCV data ...")
    raw_df, company_name = df_mod.fetch(ticker)

    # ── 2. Feature engineering ────────────────────────────────────────────────
    print("\n[2/5] Engineering features ...")
    featured_df = fe_mod.build_features(raw_df)
    print(f"  Feature matrix : {featured_df.shape[0]} rows x {len(fe_mod.FEATURE_COLS)} features")
    print(f"  Features       : {', '.join(fe_mod.FEATURE_COLS)}")

    # ── 3. Train model ────────────────────────────────────────────────────────
    print("\n[3/5] Training XGBoost (years 1-2 train / year 3 validate) ...")
    forecaster   = xm_mod.ReturnForecaster()
    train_result = forecaster.train(featured_df)

    print(f"\n  Train metrics  -> RMSE: {train_result['train_metrics']['rmse']:.4f}  "
          f"Dir-Acc: {train_result['train_metrics']['direction_accuracy']*100:.1f}%")
    print(f"  Val   metrics  -> RMSE: {train_result['val_metrics']['rmse']:.4f}  "
          f"Dir-Acc: {train_result['val_metrics']['direction_accuracy']*100:.1f}%  (out-of-sample)")

    # ── 4. Predict latest ─────────────────────────────────────────────────────
    print("\n[4/5] Predicting 30-day forward return from latest data ...")
    prediction = forecaster.predict_latest(featured_df)

    # ── 5. Reports & plots ────────────────────────────────────────────────────
    print("\n[5/5] Generating reports ...")
    reporter = rg_mod.ReportGeneratorB(
        ticker, company_name, featured_df,
        train_result, prediction,
        forecaster.feature_importance
    )
    reporter.save_json()
    reporter.save_text()
    reporter.print_summary()

    if make_plots:
        try:
            viz_mod.plot_forecast(ticker, featured_df, train_result, prediction)
        except Exception as e:
            print(f"[WARNING] Could not generate plot: {e}")

    return prediction


def main():
    args = parse_args()
    result = run(
        ticker    = args.ticker,
        threshold = args.threshold,
        make_plots= not args.no_plots,
    )
    # Exit code: 0 = PASS, 1 = FAIL (useful for scripting)
    sys.exit(0 if result['signal'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
