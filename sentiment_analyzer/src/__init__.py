"""Sentiment Analyzer Package for Stock Trading System."""

__version__ = '1.0.0'
__author__ = 'B. I. Parker Data Science and Consulting LLC'

from . import config
from .pdf_retriever import PDFRetriever
from .pdf_extractor import PDFExtractor
from .sentiment_engine import SentimentEngine
from .report_generator import ReportGenerator
from .trading_integrator import TradingIntegrator

__all__ = [
    'config',
    'PDFRetriever',
    'PDFExtractor',
    'SentimentEngine',
    'ReportGenerator',
    'TradingIntegrator'
]

# Made with Bob
