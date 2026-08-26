"""Unit tests for method recommender agent."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import pandas as pd
import pytest
from method_recommender import MethodRecommenderAgent


@pytest.fixture
def stationary_data():
    """Create stationary time-series data."""
    dates = pd.date_range('2023-01-01', periods=252)
    # Create stationary data (mean-reverting)
    data = np.random.normal(100, 2, 252)

    return pd.DataFrame({
        'date': dates,
        'close': data
    })


@pytest.fixture
def trending_data():
    """Create trending time-series data."""
    dates = pd.date_range('2023-01-01', periods=252)
    # Create strong uptrend
    trend = np.linspace(100, 150, 252)
    noise = np.random.normal(0, 1, 252)
    data = trend + noise

    return pd.DataFrame({
        'date': dates,
        'close': data
    })


@pytest.fixture
def seasonal_data():
    """Create seasonal time-series data."""
    dates = pd.date_range('2023-01-01', periods=252)
    # Create seasonal pattern (52 week pattern)
    seasonal = 10 * np.sin(2 * np.pi * np.arange(252) / 52)
    trend = np.linspace(100, 110, 252)
    noise = np.random.normal(0, 0.5, 252)
    data = trend + seasonal + noise

    return pd.DataFrame({
        'date': dates,
        'close': data
    })


class TestMethodRecommender:
    """Test MethodRecommenderAgent."""

    def test_initialization(self, stationary_data):
        """Test recommender initialization."""
        recommender = MethodRecommenderAgent(stationary_data)
        assert recommender.data is not None
        assert recommender.feature_col == 'close'

    def test_analyze_data_characteristics(self, stationary_data):
        """Test data characteristic analysis."""
        recommender = MethodRecommenderAgent(stationary_data)
        analysis = recommender.analyze_data_characteristics()

        assert 'stationarity' in analysis
        assert 'trend' in analysis
        assert 'seasonality' in analysis
        assert 'volatility' in analysis
        assert 'characteristics' in analysis

    def test_stationarity_test(self, stationary_data, trending_data):
        """Test stationarity detection."""
        rec_stat = MethodRecommenderAgent(stationary_data)
        rec_stat.analyze_data_characteristics()
        stat_result = rec_stat.analysis['stationarity']

        rec_trend = MethodRecommenderAgent(trending_data)
        rec_trend.analyze_data_characteristics()
        trend_result = rec_trend.analysis['stationarity']

        # Stationary data should have lower p-value
        assert stat_result['p_value'] is not None
        assert trend_result['p_value'] is not None

    def test_trend_analysis(self, trending_data):
        """Test trend detection."""
        recommender = MethodRecommenderAgent(trending_data)
        recommender.analyze_data_characteristics()
        trend = recommender.analysis['trend']

        assert 'slope' in trend
        assert 'r_squared' in trend
        assert 'strength' in trend
        assert 'direction' in trend

        # Trending data should have positive slope
        assert trend['slope'] > 0
        assert trend['direction'] == 'Uptrend'

    def test_seasonality_analysis(self, seasonal_data):
        """Test seasonality detection."""
        recommender = MethodRecommenderAgent(seasonal_data)
        recommender.analyze_data_characteristics()
        seasonality = recommender.analysis['seasonality']

        assert 'has_seasonality' in seasonality
        assert 'seasonal_strength' in seasonality
        assert 'period' in seasonality

    def test_volatility_analysis(self, stationary_data):
        """Test volatility analysis."""
        recommender = MethodRecommenderAgent(stationary_data)
        recommender.analyze_data_characteristics()
        volatility = recommender.analysis['volatility']

        assert 'volatility' in volatility
        assert 'coefficient_of_variation' in volatility
        assert 'level' in volatility
        assert volatility['volatility'] >= 0

    def test_recommend_methods(self, stationary_data):
        """Test method recommendations."""
        recommender = MethodRecommenderAgent(stationary_data)
        recommendations = recommender.recommend_methods()

        assert len(recommendations) > 0
        assert all(method in [m for m, _ in recommendations] for method in [
            'linear_regression', 'arima', 'exponential_smoothing',
            'prophet', 'lstm', 'xgboost'
        ])

    def test_recommendations_are_scored(self, stationary_data):
        """Test recommendations have valid scores."""
        recommender = MethodRecommenderAgent(stationary_data)
        recommendations = recommender.recommend_methods()

        for method, score in recommendations:
            assert isinstance(method, str)
            assert isinstance(score, (int, float))
            assert score >= -10  # Scores can be negative

    def test_get_detailed_recommendations(self, stationary_data):
        """Test detailed recommendations."""
        recommender = MethodRecommenderAgent(stationary_data)
        detailed = recommender.get_detailed_recommendations()

        assert len(detailed) <= 3  # At most 3 recommendations
        for rec in detailed:
            assert 'method' in rec
            assert 'score' in rec
            assert 'explanation' in rec

            explanation = rec['explanation']
            assert 'description' in explanation
            assert 'strengths' in explanation
            assert 'weaknesses' in explanation

    def test_trending_data_recommendations(self, trending_data):
        """Test recommendations for trending data."""
        recommender = MethodRecommenderAgent(trending_data)
        recommendations = recommender.recommend_methods()
        top_method = recommendations[0][0]

        # Trending data should recommend Prophet or Linear Regression
        assert top_method in ['prophet', 'linear_regression', 'exponential_smoothing']

    def test_seasonal_data_recommendations(self, seasonal_data):
        """Test recommendations for seasonal data."""
        recommender = MethodRecommenderAgent(seasonal_data)
        recommendations = recommender.recommend_methods()
        top_method = recommendations[0][0]

        # Seasonal data should recommend Prophet or ETS
        assert top_method in ['prophet', 'exponential_smoothing', 'lstm']

    def test_characteristics_summary(self, stationary_data):
        """Test characteristics summary."""
        recommender = MethodRecommenderAgent(stationary_data)
        recommender.analyze_data_characteristics()
        chars = recommender.analysis['characteristics']

        assert chars['length'] == 252
        assert chars['mean'] > 0
        assert chars['std'] >= 0
        assert chars['min'] < chars['max']
        assert not chars['has_missing']


class TestRecommenderEdgeCases:
    """Test edge cases for recommender."""

    def test_small_dataset(self):
        """Test with very small dataset."""
        dates = pd.date_range('2023-01-01', periods=30)
        data = pd.DataFrame({
            'date': dates,
            'close': np.random.normal(100, 5, 30)
        })

        recommender = MethodRecommenderAgent(data)
        recommendations = recommender.recommend_methods()

        assert len(recommendations) > 0

    def test_constant_data(self):
        """Test with constant data (no variation)."""
        dates = pd.date_range('2023-01-01', periods=100)
        data = pd.DataFrame({
            'date': dates,
            'close': np.ones(100) * 100
        })

        recommender = MethodRecommenderAgent(data)
        analysis = recommender.analyze_data_characteristics()

        assert 'volatility' in analysis
        # Volatility should be zero or near-zero
        assert analysis['volatility']['volatility'] < 0.1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
