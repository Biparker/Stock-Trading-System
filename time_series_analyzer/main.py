#!/usr/bin/env python3
"""Command-line interface for time-series stock price forecasting."""

import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main_analyzer import TimeSeriesAnalyzer


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Time-Series Stock Price Forecasting Tool',
        epilog='Example: python main.py --ticker AAPL --method auto --features close volume'
    )

    parser.add_argument(
        '--ticker',
        type=str,
        help='Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)'
    )

    parser.add_argument(
        '--method',
        type=str,
        default='auto',
        choices=['auto', 'linear_regression', 'arima', 'exponential_smoothing', 'prophet', 'lstm', 'xgboost'],
        help='Forecasting method to use (default: auto-select based on data)'
    )

    parser.add_argument(
        '--features',
        type=str,
        nargs='+',
        help='Features to use in analysis (e.g., close volume open high low)'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for historical data (YYYY-MM-DD format)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for historical data (YYYY-MM-DD format)'
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        default=False,
        help='Use interactive mode for feature selection'
    )

    args = parser.parse_args()

    # If no ticker provided, ask for it
    if not args.ticker:
        print("\n" + "="*70)
        print("TIME-SERIES STOCK PRICE FORECASTING TOOL")
        print("="*70)
        print("\nNo ticker specified. Enter a stock ticker symbol.")
        args.ticker = input("Stock Ticker (e.g., AAPL): ").strip().upper()

        if not args.ticker:
            print("Error: Ticker symbol required")
            sys.exit(1)

    # Create analyzer
    analyzer = TimeSeriesAnalyzer(args.ticker, interactive=args.interactive)

    # Prepare kwargs for run_analysis
    run_kwargs = {'method': args.method}

    if args.features:
        run_kwargs['features'] = [f.lower() for f in args.features]

    # Run analysis
    try:
        result = analyzer.run_analysis(**run_kwargs)

        if result:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        print(f"\n[ERROR] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
