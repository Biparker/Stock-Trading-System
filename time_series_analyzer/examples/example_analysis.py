#!/usr/bin/env python3
"""Example usage of the time-series analysis tool."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main_analyzer import TimeSeriesAnalyzer


def example_1_interactive():
    """Example 1: Interactive analysis with auto method selection."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Interactive Analysis with Auto Method Selection")
    print("="*70)

    analyzer = TimeSeriesAnalyzer('AAPL', interactive=True)
    result = analyzer.run_analysis(method='auto')

    if result:
        print("\n✓ Analysis completed successfully!")
        print(f"Company: {result['company']}")
        print(f"Selected Method: {result['method'].replace('_', ' ').title()}")


def example_2_prophet():
    """Example 2: Use Prophet method explicitly."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Using Prophet Method Explicitly")
    print("="*70)

    analyzer = TimeSeriesAnalyzer('MSFT', interactive=False)
    result = analyzer.run_analysis(method='prophet', features=['close', 'volume'])

    if result:
        forecast = result['forecast']['forecast']
        print(f"\nForecasted prices (next 30 days):")
        print(f"  Start: ${forecast[0]:.2f}")
        print(f"  End: ${forecast[-1]:.2f}")
        print(f"  Average: ${forecast.mean():.2f}")


def example_3_lstm():
    """Example 3: Use LSTM method for complex patterns."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Using LSTM for Complex Patterns")
    print("="*70)

    analyzer = TimeSeriesAnalyzer('GOOGL', interactive=False)
    result = analyzer.run_analysis(method='lstm', features=['close'])

    if result:
        print("\n✓ LSTM analysis completed!")
        print(f"  Forecast range: ${result['forecast']['forecast'].min():.2f} - ${result['forecast']['forecast'].max():.2f}")


def example_4_method_comparison():
    """Example 4: Compare multiple methods (manual)."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Comparing Multiple Methods")
    print("="*70)

    ticker = 'AAPL'
    methods = ['linear_regression', 'arima', 'prophet']

    for method in methods:
        try:
            print(f"\nAnalyzing with {method.replace('_', ' ').title()}...")
            analyzer = TimeSeriesAnalyzer(ticker, interactive=False)
            result = analyzer.run_analysis(method=method, features=['close'])

            if result:
                forecast = result['forecast']['forecast']
                rmse = result['forecast']['metrics'].get('rmse', 'N/A')
                print(f"  ✓ Complete - RMSE: {rmse}")
        except Exception as e:
            print(f"  ✗ Failed: {str(e)}")


def example_5_programmatic():
    """Example 5: Programmatic access to components."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Programmatic Component Access")
    print("="*70)

    from data_fetcher import DataFetcherAgent
    from method_recommender import MethodRecommenderAgent
    from forecasting_methods import get_forecaster

    # Fetch data
    print("\nFetching data for AAPL...")
    fetcher = DataFetcherAgent()
    result = fetcher.fetch_stock_data('AAPL')

    if result['status'] != 'success':
        print(f"Error: {result['message']}")
        return

    data = result['data']
    fetcher.get_summary()

    # Analyze with recommender
    print("\nAnalyzing data characteristics...")
    recommender = MethodRecommenderAgent(data)
    analysis = recommender.analyze_data_characteristics()

    print(f"Stationarity: {analysis['stationarity']['interpretation']}")
    print(f"Trend: {analysis['trend']['direction']} ({analysis['trend']['strength']})")
    print(f"Seasonality: {'Detected' if analysis['seasonality']['has_seasonality'] else 'Not detected'}")

    # Get recommendations
    print("\nTop 3 recommended methods:")
    recommendations = recommender.get_detailed_recommendations()
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec['method'].replace('_', ' ').title()} (Score: {rec['score']})")

    # Use top recommended method
    top_method = recommendations[0]['method']
    print(f"\nUsing top recommended method: {top_method.replace('_', ' ').title()}")

    forecaster = get_forecaster(top_method, data, feature_col='close')
    forecaster.fit()
    forecaster.predict()
    forecast = forecaster.get_forecast()

    print(f"Forecast generated for {len(forecast['forecast'])} days")
    print(f"  Mean: ${forecast['forecast'].mean():.2f}")
    print(f"  Range: ${forecast['confidence_interval']['lower'].min():.2f} - ${forecast['confidence_interval']['upper'].max():.2f}")


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║     TIME-SERIES STOCK PRICE FORECASTING TOOL - USAGE EXAMPLES            ║
╚══════════════════════════════════════════════════════════════════════════╝

This script demonstrates various ways to use the time-series analysis tool.

Choose an example to run:
  1. Interactive analysis with auto method selection
  2. Using Prophet method explicitly
  3. Using LSTM for complex patterns
  4. Comparing multiple methods
  5. Programmatic component access (detailed analysis)

Note: Some examples may take 1-3 minutes depending on your system.
    """)

    choice = input("\nSelect example (1-5) or 'q' to quit: ").strip()

    examples = {
        '1': example_1_interactive,
        '2': example_2_prophet,
        '3': example_3_lstm,
        '4': example_4_method_comparison,
        '5': example_5_programmatic,
    }

    if choice in examples:
        try:
            examples[choice]()
        except Exception as e:
            print(f"\n❌ Error running example: {str(e)}")
            import traceback
            traceback.print_exc()
    elif choice.lower() != 'q':
        print("Invalid choice")
