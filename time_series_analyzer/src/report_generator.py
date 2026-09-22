"""Report generator for forecast analysis and predictions."""

import json
import os
import pandas as pd
from datetime import timedelta
from config import OUTPUT_DIR

os.makedirs(OUTPUT_DIR, exist_ok=True)


class ReportGenerator:
    """Generate detailed reports of forecasting analysis."""

    def __init__(self, ticker, company_name, analysis, selected_method, forecast_result, data):
        self.ticker = ticker
        self.company_name = company_name
        self.analysis = analysis
        self.selected_method = selected_method
        self.forecast_result = forecast_result
        self.data = data

    def generate_text_report(self, save_path=None):
        """
        Generate detailed text report.

        Args:
            save_path (str): Path to save the report

        Returns:
            str: Formatted report text
        """
        report = self._build_text_report()

        if save_path is None:
            save_path = os.path.join(OUTPUT_DIR, f'{self.ticker}_forecast_report.txt')

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"[OK] Text report saved to {save_path}")
        return report

    def generate_json_report(self, save_path=None):
        """
        Generate JSON report with all data.

        Args:
            save_path (str): Path to save the report

        Returns:
            dict: Report data
        """
        report_data = self._build_json_report()

        if save_path is None:
            save_path = os.path.join(OUTPUT_DIR, f'{self.ticker}_forecast_report.json')

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)

        print(f"[OK] JSON report saved to {save_path}")
        return report_data

    def _build_text_report(self):
        """Build text report content."""
        last_date = pd.to_datetime(self.data['date'].iloc[-1])
        forecast_start = last_date + timedelta(days=1)
        forecast_dates = pd.date_range(start=forecast_start, periods=len(self.forecast_result['forecast']), freq='B')

        report = []
        report.append("="*80)
        report.append("STOCK PRICE FORECAST ANALYSIS REPORT")
        report.append("="*80)

        # Executive Summary
        report.append("\n[EXECUTIVE SUMMARY]")
        report.append(f"Stock:              {self.ticker} ({self.company_name})")
        report.append(f"Analysis Period:    {self.data['date'].iloc[0].date()} to {self.data['date'].iloc[-1].date()}")
        report.append(f"Forecast Period:    {forecast_start.date()} to {forecast_dates[-1].date()}")
        report.append(f"Historical Records: {len(self.data)}")
        report.append(f"Forecasted Days:    {len(self.forecast_result['forecast'])}")
        report.append(f"Current Price:      ${self.data['close'].iloc[-1]:.2f}")

        # Data Summary
        report.append("\n[DATA SUMMARY]")
        report.append(f"Start Price:        ${self.data['close'].iloc[0]:.2f}")
        report.append(f"End Price:          ${self.data['close'].iloc[-1]:.2f}")
        report.append(f"Min Price:          ${self.data['close'].min():.2f}")
        report.append(f"Max Price:          ${self.data['close'].max():.2f}")
        report.append(f"Average Price:      ${self.data['close'].mean():.2f}")
        change = ((self.data['close'].iloc[-1] - self.data['close'].iloc[0]) / self.data['close'].iloc[0]) * 100
        report.append(f"Price Change:       {change:+.2f}%")
        report.append(f"Volatility:         {self.data['close'].pct_change().std() * 100:.2f}%")

        # Data Characteristics Analysis
        report.append("\n[DATA CHARACTERISTICS ANALYSIS]")
        analysis = self.analysis

        report.append("\nStationarity:")
        report.append(f"  Status:           {analysis['stationarity']['interpretation']}")
        if analysis['stationarity']['p_value']:
            report.append(f"  ADF p-value:      {analysis['stationarity']['p_value']:.6f}")

        report.append("\nTrend:")
        report.append(f"  Direction:        {analysis['trend']['direction']}")
        report.append(f"  Strength:         {analysis['trend']['strength']}")
        report.append(f"  R-squared:        {analysis['trend']['r_squared']:.4f}")

        report.append("\nSeasonality:")
        report.append(f"  Detected:         {'Yes' if analysis['seasonality']['has_seasonality'] else 'No'}")
        report.append(f"  Strength:         {analysis['seasonality']['seasonal_strength']:.4f}")
        report.append(f"  Interpretation:   {analysis['seasonality']['interpretation']}")

        report.append("\nVolatility:")
        report.append(f"  Level:            {analysis['volatility']['level']}")
        report.append(f"  Daily Volatility: {analysis['volatility']['volatility']:.2f}%")
        report.append(f"  Coeff of Var:     {analysis['volatility']['coefficient_of_variation']:.4f}")

        # Selected Method and Explanation
        report.append(f"\n[SELECTED FORECASTING METHOD]")
        report.append(f"Method:             {self.selected_method.replace('_', ' ').title()}")

        # Forecast Results
        report.append("\n[FORECAST RESULTS (95% Confidence Interval)]")
        report.append(f"\n{'Date':<12} {'Forecast':<15} {'Lower Bound':<15} {'Upper Bound':<15} {'Range':<10}")
        report.append("-" * 67)

        for i, (date, forecast_val) in enumerate(zip(forecast_dates, self.forecast_result['forecast'])):
            lower = self.forecast_result['confidence_interval']['lower'][i]
            upper = self.forecast_result['confidence_interval']['upper'][i]
            range_val = upper - lower

            report.append(f"{date.date()!s:<12} ${forecast_val:<14.2f} ${lower:<14.2f} ${upper:<14.2f} ${range_val:<9.2f}")

        # Summary Statistics
        report.append("\n[FORECAST SUMMARY STATISTICS]")
        forecast = self.forecast_result['forecast']
        report.append(f"Mean Forecast:      ${forecast.mean():.2f}")
        report.append(f"Min Forecast:       ${forecast.min():.2f}")
        report.append(f"Max Forecast:       ${forecast.max():.2f}")
        report.append(f"Forecast Change:    {((forecast[-1] - self.data['close'].iloc[-1]) / self.data['close'].iloc[-1] * 100):+.2f}%")

        # Model Performance
        report.append("\n[MODEL PERFORMANCE METRICS]")
        metrics = self.forecast_result['metrics']
        report.append(f"RMSE:               {metrics.get('rmse', 'N/A')}")
        report.append(f"MAE:                {metrics.get('mae', 'N/A')}")
        report.append(f"MAPE:               {metrics.get('mape', 'N/A')}")

        # Risk Assessment
        report.append("\n[RISK ASSESSMENT]")
        report.append("\nConfidence Interval Width:")
        ci_widths = self.forecast_result['confidence_interval']['upper'] - self.forecast_result['confidence_interval']['lower']
        report.append(f"  Average:          ${ci_widths.mean():.2f}")
        report.append(f"  Min:              ${ci_widths.min():.2f}")
        report.append(f"  Max:              ${ci_widths.max():.2f}")

        report.append("\nKey Risk Factors:")
        if analysis['volatility']['level'] == 'High':
            report.append("  ⚠️  High volatility detected - predictions less reliable")
        if not analysis['stationarity']['is_stationary']:
            report.append("  ⚠️  Non-stationary data - trends may not continue")
        if analysis['characteristics']['length'] < 100:
            report.append("  ⚠️  Limited historical data - forecasts less reliable")

        # Disclaimers
        report.append("\n[DISCLAIMERS & LIMITATIONS]")
        report.append("• This forecast is based on historical patterns and may not predict future prices")
        report.append("• Stock prices are influenced by many factors not captured in this analysis")
        report.append("• Market conditions and unexpected events can cause significant deviations")
        report.append("• Do not use this forecast as sole basis for investment decisions")
        report.append("• Past performance does not guarantee future results")
        report.append("• Consult financial advisors before making investment decisions")

        report.append("\n" + "="*80)

        return "\n".join(report)

    def _build_json_report(self):
        """Build JSON report content."""
        last_date = pd.to_datetime(self.data['date'].iloc[-1])
        forecast_start = last_date + timedelta(days=1)
        forecast_dates = pd.date_range(start=forecast_start, periods=len(self.forecast_result['forecast']), freq='B')

        forecast_data = []
        for i, (date, forecast_val) in enumerate(zip(forecast_dates, self.forecast_result['forecast'])):
            forecast_data.append({
                'date': date.isoformat(),
                'forecast': float(forecast_val),
                'lower_bound': float(self.forecast_result['confidence_interval']['lower'][i]),
                'upper_bound': float(self.forecast_result['confidence_interval']['upper'][i]),
            })

        # Build price history for dashboard two-panel chart.
        # Includes train/val split index so the chart can colour each segment.
        split_idx = int(len(self.data) * 0.8)
        price_history = [
            {
                'date': str(row['date'])[:10],
                'close': float(row['close']),
                'split': 'train' if i < split_idx else 'val',
            }
            for i, row in self.data[['date', 'close']].iterrows()
        ]

        return {
            'metadata': {
                'ticker': self.ticker,
                'company_name': self.company_name,
                'analysis_start_date': self.data['date'].iloc[0].isoformat(),
                'analysis_end_date': self.data['date'].iloc[-1].isoformat(),
                'forecast_start_date': forecast_start.isoformat(),
                'forecast_end_date': forecast_dates[-1].isoformat(),
                'historical_records': len(self.data),
                'forecast_periods': len(self.forecast_result['forecast']),
            },
            'current_metrics': {
                'current_price': float(self.data['close'].iloc[-1]),
                'start_price': float(self.data['close'].iloc[0]),
                'min_price': float(self.data['close'].min()),
                'max_price': float(self.data['close'].max()),
                'avg_price': float(self.data['close'].mean()),
                'price_change_pct': float(((self.data['close'].iloc[-1] - self.data['close'].iloc[0]) / self.data['close'].iloc[0]) * 100),
                'volatility_pct': float(self.data['close'].pct_change().std() * 100),
            },
            'data_characteristics': {
                'stationarity': self.analysis['stationarity'],
                'trend': self.analysis['trend'],
                'seasonality': self.analysis['seasonality'],
                'volatility': self.analysis['volatility'],
            },
            'selected_method': self.selected_method,
            'price_history': price_history,
            'forecast_results': forecast_data,
            'forecast_summary': {
                'mean': float(self.forecast_result['forecast'].mean()),
                'min': float(self.forecast_result['forecast'].min()),
                'max': float(self.forecast_result['forecast'].max()),
                'change_pct': float(((self.forecast_result['forecast'][-1] - self.data['close'].iloc[-1]) / self.data['close'].iloc[-1] * 100)),
            },
            'model_metrics': self.forecast_result['metrics'],
        }

    def print_report(self):
        """Print report to console."""
        print(f"\n[OK] Report generated and saved to {OUTPUT_DIR}")
