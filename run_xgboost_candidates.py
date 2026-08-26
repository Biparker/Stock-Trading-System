#!/usr/bin/env python3
"""Run XGBoost forecasting on all 7 candidate stocks."""

import sys
import os
from datetime import datetime

# Add time_series_analyzer/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'time_series_analyzer', 'src'))

from main_analyzer import TimeSeriesAnalyzer

# 7 Candidate stocks from candidate_stocks_list.txt
CANDIDATE_STOCKS = [
    'AMGN',   # Amgen - Composite Score: 95
    'MSFT',   # Microsoft - Composite Score: 90
    'ADBE',   # Adobe - Composite Score: 90
    'QCOM',   # Qualcomm - Composite Score: 90
    'GILD',   # Gilead Sciences - Composite Score: 90
    'GOOGL',  # Alphabet/Google - Composite Score: 85
    'JNJ'     # Johnson & Johnson - Composite Score: 85
]

def main():
    """Run XGBoost forecasting on all candidate stocks."""
    print("="*80)
    print("XGBOOST FORECASTING FOR 7 CANDIDATE STOCKS")
    print("="*80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nStocks to analyze: {', '.join(CANDIDATE_STOCKS)}")
    print(f"Method: XGBoost")
    print(f"Features: close, volume (default)")
    print("\n" + "="*80 + "\n")
    
    results = {}
    successful = []
    failed = []
    
    for i, ticker in enumerate(CANDIDATE_STOCKS, 1):
        print(f"\n[{i}/{len(CANDIDATE_STOCKS)}] Processing {ticker}...")
        print("-" * 80)
        
        try:
            # Create analyzer with non-interactive mode
            analyzer = TimeSeriesAnalyzer(ticker, interactive=False)
            
            # Run analysis with XGBoost method
            result = analyzer.run_analysis(method='xgboost')
            
            if result:
                results[ticker] = 'SUCCESS'
                successful.append(ticker)
                print(f"[OK] {ticker} completed successfully")
            else:
                results[ticker] = 'FAILED'
                failed.append(ticker)
                print(f"[FAIL] {ticker} failed")
                
        except Exception as e:
            results[ticker] = f'ERROR: {str(e)}'
            failed.append(ticker)
            print(f"[ERROR] {ticker} error: {str(e)}")
        
        print("-" * 80)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nTotal stocks: {len(CANDIDATE_STOCKS)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        print(f"\n[OK] Successful stocks: {', '.join(successful)}")
    
    if failed:
        print(f"\n[FAIL] Failed stocks: {', '.join(failed)}")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nOutput files saved to: time_series_analyzer/output/")
    print("  - [TICKER]_forecast_report.txt")
    print("  - [TICKER]_forecast_report.json")
    print("  - plots/[TICKER]_*.png")
    print("="*80)
    
    # Return exit code
    return 0 if len(failed) == 0 else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

# Made with Bob
