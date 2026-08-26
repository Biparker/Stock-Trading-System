"""Main orchestrator for time-series analysis workflow."""

import os
import sys
from data_fetcher import DataFetcherAgent
from feature_selector import FeatureSelector
from method_recommender import MethodRecommenderAgent
from forecasting_methods import get_forecaster
from visualizer import TimeSeriesVisualizer
from report_generator import ReportGenerator
from config import PLOTS_DIR

os.makedirs(PLOTS_DIR, exist_ok=True)


class TimeSeriesAnalyzer:
    """Main orchestrator for complete time-series analysis workflow."""

    def __init__(self, ticker, interactive=True):
        self.ticker = ticker.upper()
        self.interactive = interactive
        self.data = None
        self.data_fetcher = None
        self.recommender = None
        self.selected_features = []
        self.selected_method = None
        self.forecast_result = None

    def run_analysis(self, method='auto', features=None):
        """
        Run complete time-series analysis workflow.

        Args:
            method (str): Forecasting method ('auto' for recommendation, or specific method)
            features (list): Features to use (None for interactive selection)

        Returns:
            dict: Complete analysis results
        """
        print("\n" + "="*70)
        print(f"TIME-SERIES STOCK PRICE FORECASTING ANALYSIS - {self.ticker}")
        print("="*70)

        # Step 1: Fetch data
        print(f"\n[STEP 1/7] Fetching stock data for {self.ticker}...")
        self.data_fetcher = DataFetcherAgent()
        result = self.data_fetcher.fetch_stock_data(self.ticker)

        if result['status'] != 'success':
            print(f"[ERROR] Error: {result['message']}")
            return None

        self.data = result['data']
        self.data_fetcher.get_summary()

        # Step 2: Feature selection
        print(f"\n[STEP 2/7] Feature selection for {self.ticker}...")
        selector = FeatureSelector(self.data)
        self.selected_features = selector.get_selected_data(
            interactive=self.interactive,
            feature_list=features
        )
        print(f"[OK] Selected features for {self.ticker}: {', '.join(self.selected_features.columns[1:].tolist())}")

        # Step 3: Data analysis
        print(f"\n[STEP 3/7] Analyzing data characteristics for {self.ticker}...")
        self.recommender = MethodRecommenderAgent(self.data, feature_col='close')
        self.recommender.analyze_data_characteristics()
        self.recommender.print_analysis_report()

        # Step 4: Select forecasting method
        print(f"\n[STEP 4/7] Selecting forecasting method for {self.ticker}...")
        if method.lower() == 'auto':
            recommendations = self.recommender.get_detailed_recommendations()
            self.selected_method = recommendations[0]['method']
            print(f"[OK] Auto-selected for {self.ticker}: {self.selected_method.replace('_', ' ').title()}")
        else:
            self.selected_method = method
            print(f"[OK] Using specified method for {self.ticker}: {method.replace('_', ' ').title()}")

        # Step 5: Fit model and forecast
        print(f"\n[STEP 5/7] Training model and generating forecast for {self.ticker}...")
        try:
            forecaster = get_forecaster(self.selected_method, self.data, feature_col='close')
            forecaster.fit()
            forecaster.predict()
            self.forecast_result = forecaster.get_forecast()
            print(f"[OK] Forecast generated successfully for {self.ticker}")
            print(f"  - Forecasted {len(self.forecast_result['forecast'])} periods")
            print(f"  - RMSE: {self.forecast_result['metrics'].get('rmse', 'N/A'):.2f}")
            print(f"  - MAE: {self.forecast_result['metrics'].get('mae', 'N/A'):.2f}")
        except Exception as e:
            print(f"[ERROR] Error during forecasting for {self.ticker}: {str(e)}")
            return None

        # Step 6: Visualizations
        print(f"\n[STEP 6/7] Creating visualizations for {self.ticker}...")
        try:
            visualizer = TimeSeriesVisualizer(self.data, self.ticker)

            # Historical data plot
            hist_plot_path = os.path.join(PLOTS_DIR, f'{self.ticker}_historical.png')
            print(f"  Creating historical plot for {self.ticker}...")
            visualizer.plot_historical_data(save_path=hist_plot_path)

            # Forecast plot
            forecast_plot_path = os.path.join(PLOTS_DIR, f'{self.ticker}_forecast_{self.selected_method}.png')
            print(f"  Creating forecast plot for {self.ticker}...")
            visualizer.plot_forecast(self.forecast_result, method_name=self.selected_method,
                                   save_path=forecast_plot_path)

            # Decomposition plot
            decomp_plot_path = os.path.join(PLOTS_DIR, f'{self.ticker}_decomposition.png')
            print(f"  Creating decomposition plot for {self.ticker}...")
            visualizer.plot_decomposition(save_path=decomp_plot_path)

            print(f"[OK] Plots saved to {PLOTS_DIR}")
        except Exception as e:
            print(f"[WARNING] Warning: Could not create visualizations for {self.ticker}: {str(e)}")
            import traceback
            traceback.print_exc()

        # Step 7: Generate reports
        print(f"\n[STEP 7/7] Generating reports for {self.ticker}...")
        report_gen = ReportGenerator(
            self.ticker,
            self.data_fetcher.company_name,
            self.recommender.analysis,
            self.selected_method,
            self.forecast_result,
            self.data
        )

        text_report_path = report_gen.generate_text_report()
        json_report_path = report_gen.generate_json_report()
        report_gen.print_report()

        print("\n" + "="*70)
        print(f"ANALYSIS COMPLETE FOR {self.ticker}!")
        print("="*70)
        print(f"\nOutput files for {self.ticker}:")
        print(f"  - Plots: {PLOTS_DIR}")
        print(f"  - Text Report: {text_report_path}")
        print(f"  - JSON Report: {json_report_path}")

        return {
            'data': self.data,
            'forecast': self.forecast_result,
            'method': self.selected_method,
            'analysis': self.recommender.analysis,
            'company': self.data_fetcher.company_name,
        }


def main():
    """Example usage of TimeSeriesAnalyzer."""
    # Example: Analyze Apple stock
    analyzer = TimeSeriesAnalyzer('AAPL', interactive=False)
    result = analyzer.run_analysis(method='auto', features=['close', 'volume'])

    if result:
        print("\n[OK] Analysis successful!")
    else:
        print("\n[ERROR] Analysis failed!")


if __name__ == '__main__':
    main()
