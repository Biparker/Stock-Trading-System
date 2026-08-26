"""Unit tests for forecasting methods."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import pandas as pd
import pytest
from forecasting_methods import (
    LinearRegressionForecaster,
    ARIMAForecaster,
    ExponentialSmoothingForecaster,
    get_forecaster
)


@pytest.fixture
def sample_data():
    """Create sample time-series data for testing."""
    dates = pd.date_range('2023-01-01', periods=252)
    # Create realistic stock price data with trend and noise
    trend = np.linspace(100, 120, 252)
    noise = np.random.normal(0, 2, 252)
    prices = trend + noise

    return pd.DataFrame({
        'date': dates,
        'close': prices,
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'volume': np.random.randint(1000000, 5000000, 252)
    })


class TestLinearRegressionForecaster:
    """Test LinearRegressionForecaster."""

    def test_fit(self, sample_data):
        """Test model fitting."""
        forecaster = LinearRegressionForecaster(sample_data)
        forecaster.fit()

        assert forecaster.model is not None
        assert 'rmse' in forecaster.metrics
        assert 'mae' in forecaster.metrics

    def test_predict(self, sample_data):
        """Test prediction."""
        forecaster = LinearRegressionForecaster(sample_data, forecast_periods=20)
        forecaster.fit()
        forecast = forecaster.predict()

        assert len(forecast) == 20
        assert not np.isnan(forecast).any()
        assert 'lower' in forecaster.confidence_interval
        assert 'upper' in forecaster.confidence_interval

    def test_confidence_intervals(self, sample_data):
        """Test confidence intervals are valid."""
        forecaster = LinearRegressionForecaster(sample_data, forecast_periods=20)
        forecaster.fit()
        forecaster.predict()

        lower = forecaster.confidence_interval['lower']
        upper = forecaster.confidence_interval['upper']
        forecast = forecaster.forecast

        assert np.all(lower < forecast)
        assert np.all(forecast < upper)
        assert np.all(upper > lower)


class TestARIMAForecaster:
    """Test ARIMAForecaster."""

    def test_fit(self, sample_data):
        """Test ARIMA fitting."""
        forecaster = ARIMAForecaster(sample_data)
        forecaster.fit()

        assert forecaster.model is not None
        assert 'rmse' in forecaster.metrics

    def test_predict(self, sample_data):
        """Test ARIMA prediction."""
        forecaster = ARIMAForecaster(sample_data, forecast_periods=20)
        forecaster.fit()
        forecast = forecaster.predict()

        assert len(forecast) == 20
        assert not np.isnan(forecast).any()

    def test_confidence_intervals(self, sample_data):
        """Test ARIMA confidence intervals."""
        forecaster = ARIMAForecaster(sample_data, forecast_periods=20)
        forecaster.fit()
        forecaster.predict()

        lower = forecaster.confidence_interval['lower']
        upper = forecaster.confidence_interval['upper']

        assert len(lower) == 20
        assert len(upper) == 20
        assert np.all(upper > lower)


class TestExponentialSmoothingForecaster:
    """Test ExponentialSmoothingForecaster."""

    def test_fit(self, sample_data):
        """Test ETS fitting."""
        forecaster = ExponentialSmoothingForecaster(sample_data)
        forecaster.fit()

        assert forecaster.model is not None
        assert 'mae' in forecaster.metrics

    def test_predict(self, sample_data):
        """Test ETS prediction."""
        forecaster = ExponentialSmoothingForecaster(sample_data, forecast_periods=20)
        forecaster.fit()
        forecast = forecaster.predict()

        assert len(forecast) == 20
        assert not np.isnan(forecast).any()

    def test_metrics(self, sample_data):
        """Test metrics are calculated."""
        forecaster = ExponentialSmoothingForecaster(sample_data, forecast_periods=20)
        forecaster.fit()

        metrics = forecaster.get_metrics()
        assert 'rmse' in metrics
        assert metrics['rmse'] >= 0
        assert metrics['mae'] >= 0


class TestFactoryFunction:
    """Test the get_forecaster factory function."""

    def test_get_all_methods(self, sample_data):
        """Test all methods can be retrieved."""
        methods = [
            'linear_regression',
            'arima',
            'exponential_smoothing',
        ]

        for method in methods:
            forecaster = get_forecaster(method, sample_data)
            assert forecaster is not None

    def test_invalid_method(self, sample_data):
        """Test invalid method raises error."""
        with pytest.raises(ValueError):
            get_forecaster('invalid_method', sample_data)

    def test_forecaster_workflow(self, sample_data):
        """Test complete forecaster workflow."""
        forecaster = get_forecaster('linear_regression', sample_data)
        forecaster.fit()
        forecaster.predict()
        result = forecaster.get_forecast()

        assert 'forecast' in result
        assert 'confidence_interval' in result
        assert 'metrics' in result
        assert len(result['forecast']) > 0


class TestForecastAccuracy:
    """Test forecast accuracy metrics."""

    def test_rmse_calculation(self, sample_data):
        """Test RMSE is calculated correctly."""
        forecaster = LinearRegressionForecaster(sample_data)
        forecaster.fit()

        metrics = forecaster.get_metrics()
        rmse = metrics['rmse']

        # RMSE should be positive and less than data std
        assert rmse >= 0
        assert rmse < sample_data['close'].std() * 2

    def test_mae_calculation(self, sample_data):
        """Test MAE is calculated correctly."""
        forecaster = LinearRegressionForecaster(sample_data)
        forecaster.fit()

        metrics = forecaster.get_metrics()
        mae = metrics['mae']

        # MAE should be positive
        assert mae >= 0
        assert mae < sample_data['close'].max()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
