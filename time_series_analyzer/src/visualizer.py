"""Visualizer for time-series forecasts and analysis."""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for Windows
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import pandas as pd
from datetime import timedelta
import os
from config import PLOT_FIGSIZE, PLOT_DPI, PLOT_CONFIDENCE_ALPHA, PLOTS_DIR

# Create output directories
os.makedirs(PLOTS_DIR, exist_ok=True)


class TimeSeriesVisualizer:
    """Create visualizations for time-series forecasts."""

    def __init__(self, data, ticker, forecast_days=None):
        self.data = data
        self.ticker = ticker
        self.forecast_days = forecast_days
        sns.set_style("darkgrid")
        plt.rcParams['figure.figsize'] = PLOT_FIGSIZE
        plt.rcParams['figure.dpi'] = PLOT_DPI

    def plot_historical_data(self, feature='close', save_path=None):
        """
        Plot historical time-series data.

        Args:
            feature (str): Feature column to plot
            save_path (str): Path to save the figure
        """
        fig, ax = plt.subplots(figsize=PLOT_FIGSIZE)

        ax.plot(self.data['date'], self.data[feature], linewidth=2, color='steelblue', label=feature.title())
        ax.set_xlabel('Date', fontsize=11, fontweight='bold')
        ax.set_ylabel('Price ($)', fontsize=11, fontweight='bold')
        ax.set_title(f'{self.ticker} - Historical {feature.title()} Data', fontsize=13, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Format x-axis
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=PLOT_DPI, bbox_inches='tight')
            print(f"[OK] Saved plot to {save_path}")
            plt.close(fig)

        return fig, ax

    def plot_forecast(self, forecast_data, feature='close', method_name='', save_path=None):
        """
        Plot forecast with confidence intervals.

        Args:
            forecast_data (dict): Contains 'forecast', 'confidence_interval'
            feature (str): Feature column name
            method_name (str): Name of forecasting method
            save_path (str): Path to save the figure
        """
        fig, ax = plt.subplots(figsize=PLOT_FIGSIZE)

        # Historical data
        ax.plot(self.data['date'], self.data[feature], linewidth=2.5, color='steelblue',
                label='Historical Data', zorder=3)

        # Calculate forecast dates
        last_date = pd.to_datetime(self.data['date'].iloc[-1])
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1),
                                       periods=len(forecast_data['forecast']), freq='B')

        # Forecast line
        ax.plot(forecast_dates, forecast_data['forecast'], linewidth=2.5, color='darkgreen',
                linestyle='--', label='Forecast', zorder=3)

        # Confidence interval
        ci = forecast_data['confidence_interval']
        ax.fill_between(forecast_dates, ci['lower'], ci['upper'],
                        alpha=PLOT_CONFIDENCE_ALPHA, color='darkgreen',
                        label='95% Confidence Interval')

        # Vertical line at split point
        ax.axvline(x=last_date, color='red', linestyle=':', linewidth=1.5, alpha=0.7)

        ax.set_xlabel('Date', fontsize=11, fontweight='bold')
        ax.set_ylabel('Price ($)', fontsize=11, fontweight='bold')
        title = f'{self.ticker} - Forecast ({method_name})' if method_name else f'{self.ticker} - Forecast'
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Format x-axis
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=PLOT_DPI, bbox_inches='tight')
            print(f"[OK] Saved plot to {save_path}")
            plt.close(fig)

        return fig, ax

    def plot_forecast_comparison(self, forecasts_dict, feature='close', save_path=None):
        """
        Compare multiple forecasts on same plot.

        Args:
            forecasts_dict (dict): {method_name: forecast_data}
            feature (str): Feature column name
            save_path (str): Path to save the figure
        """
        fig, ax = plt.subplots(figsize=(16, 7))

        # Historical data
        ax.plot(self.data['date'], self.data[feature], linewidth=2.5, color='navy',
                label='Historical Data', zorder=3)

        # Forecast dates
        last_date = pd.to_datetime(self.data['date'].iloc[-1])
        num_forecasts = len(list(forecasts_dict.values())[0]['forecast'])
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1),
                                       periods=num_forecasts, freq='B')

        # Colors for different methods
        colors = ['darkgreen', 'darkred', 'darkorange', 'purple', 'brown', 'pink']

        for idx, (method_name, forecast_data) in enumerate(forecasts_dict.items()):
            color = colors[idx % len(colors)]

            ax.plot(forecast_dates, forecast_data['forecast'], linewidth=2,
                   linestyle='--', color=color, label=f'{method_name} Forecast', zorder=2)

            ci = forecast_data['confidence_interval']
            ax.fill_between(forecast_dates, ci['lower'], ci['upper'],
                           alpha=PLOT_CONFIDENCE_ALPHA * 0.5, color=color, zorder=1)

        # Vertical line at split point
        ax.axvline(x=last_date, color='red', linestyle=':', linewidth=2, alpha=0.7, label='Forecast Start')

        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Price ($)', fontsize=12, fontweight='bold')
        ax.set_title(f'{self.ticker} - Multi-Model Forecast Comparison', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10, ncol=2)
        ax.grid(True, alpha=0.3)

        # Format x-axis
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=PLOT_DPI, bbox_inches='tight')
            print(f"[OK] Saved plot to {save_path}")
            plt.close(fig)

        return fig, ax

    def plot_metrics_comparison(self, metrics_dict, save_path=None):
        """
        Compare model metrics across methods.

        Args:
            metrics_dict (dict): {method_name: metrics}
            save_path (str): Path to save the figure
        """
        methods = list(metrics_dict.keys())
        metrics = ['rmse', 'mae', 'mape']

        fig, axes = plt.subplots(1, 3, figsize=(16, 5))

        for ax_idx, metric in enumerate(metrics):
            values = [metrics_dict[method].get(metric, 0) for method in methods]

            bars = axes[ax_idx].bar(methods, values, color='steelblue', alpha=0.7, edgecolor='black')
            axes[ax_idx].set_ylabel(metric.upper(), fontsize=11, fontweight='bold')
            axes[ax_idx].set_title(f'{metric.upper()} Comparison', fontsize=12, fontweight='bold')
            axes[ax_idx].grid(True, alpha=0.3, axis='y')

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                axes[ax_idx].text(bar.get_x() + bar.get_width()/2., height,
                                f'{height:.2f}',
                                ha='center', va='bottom', fontsize=9)

            plt.setp(axes[ax_idx].xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=PLOT_DPI, bbox_inches='tight')
            print(f"[OK] Saved plot to {save_path}")
            plt.close(fig)

        return fig, axes

    def plot_decomposition(self, feature='close', save_path=None):
        """
        Plot seasonal decomposition of the series.

        Args:
            feature (str): Feature column to decompose
            save_path (str): Path to save the figure
        """
        from statsmodels.tsa.seasonal import seasonal_decompose

        try:
            series = self.data[feature]
            period = min(252, len(series) // 4)

            decomposition = seasonal_decompose(series, model='additive', period=period)

            fig, axes = plt.subplots(4, 1, figsize=(14, 10))

            # Original
            axes[0].plot(self.data['date'], series, linewidth=1.5, color='steelblue')
            axes[0].set_ylabel('Original', fontsize=10, fontweight='bold')
            axes[0].set_title(f'{self.ticker} - Seasonal Decomposition', fontsize=13, fontweight='bold')
            axes[0].grid(True, alpha=0.3)

            # Trend
            axes[1].plot(self.data['date'], decomposition.trend, linewidth=1.5, color='darkgreen')
            axes[1].set_ylabel('Trend', fontsize=10, fontweight='bold')
            axes[1].grid(True, alpha=0.3)

            # Seasonal
            axes[2].plot(self.data['date'], decomposition.seasonal, linewidth=1.5, color='darkorange')
            axes[2].set_ylabel('Seasonal', fontsize=10, fontweight='bold')
            axes[2].grid(True, alpha=0.3)

            # Residual
            axes[3].plot(self.data['date'], decomposition.resid, linewidth=1.5, color='darkred')
            axes[3].set_ylabel('Residual', fontsize=10, fontweight='bold')
            axes[3].set_xlabel('Date', fontsize=10, fontweight='bold')
            axes[3].grid(True, alpha=0.3)

            # Format x-axis
            for ax in axes:
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

            plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha='right')
            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=PLOT_DPI, bbox_inches='tight')
                print(f"[OK] Saved plot to {save_path}")
                plt.close(fig)

            return fig, axes

        except Exception as e:
            print(f"[WARNING]  Could not create decomposition plot: {str(e)}")
            return None, None


def main():
    """Example usage of TimeSeriesVisualizer."""
    # Create sample data
    dates = pd.date_range('2023-01-01', periods=252)
    prices = 100 + np.cumsum(np.random.normal(0.5, 2, 252))

    data = pd.DataFrame({
        'date': dates,
        'close': prices
    })

    visualizer = TimeSeriesVisualizer(data, 'SAMPLE')
    visualizer.plot_historical_data(save_path=os.path.join(PLOTS_DIR, 'historical.png'))

    print("[OK] Visualization complete")


if __name__ == '__main__':
    main()
