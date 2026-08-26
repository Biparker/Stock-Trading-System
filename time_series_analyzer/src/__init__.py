"""Time-Series Stock Price Analysis Tool."""

__version__ = '1.0.0'

from .main_analyzer import TimeSeriesAnalyzer
from .data_fetcher import DataFetcherAgent
from .method_recommender import MethodRecommenderAgent
from .forecasting_methods import get_forecaster
from .visualizer import TimeSeriesVisualizer
from .report_generator import ReportGenerator
from .feature_selector import FeatureSelector

__all__ = [
    'TimeSeriesAnalyzer',
    'DataFetcherAgent',
    'MethodRecommenderAgent',
    'get_forecaster',
    'TimeSeriesVisualizer',
    'ReportGenerator',
    'FeatureSelector',
]
