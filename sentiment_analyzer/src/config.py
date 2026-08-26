"""Configuration constants for sentiment analysis agent."""

import os
from datetime import datetime, timedelta

# Directory Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
CREDENTIALS_DIR = os.path.join(DATA_DIR, 'credentials')
SAMPLE_REPORTS_DIR = os.path.join(DATA_DIR, 'sample_reports')
SENTIMENT_REPORTS_DIR = os.path.join(OUTPUT_DIR, 'sentiment_reports')
TRADING_SIGNALS_DIR = os.path.join(OUTPUT_DIR, 'trading_signals')

# Create directories if they don't exist
for directory in [DATA_DIR, OUTPUT_DIR, MODELS_DIR, CREDENTIALS_DIR, 
                  SAMPLE_REPORTS_DIR, SENTIMENT_REPORTS_DIR, TRADING_SIGNALS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Merrill Lynch API Configuration
MERRILL_BASE_URL = "https://www.merrilledge.com"
MERRILL_LOGIN_URL = f"{MERRILL_BASE_URL}/login"
MERRILL_RESEARCH_URL = f"{MERRILL_BASE_URL}/research"
MERRILL_TIMEOUT = 30  # seconds
MERRILL_MAX_RETRIES = 3

# PDF Retrieval Configuration
DOWNLOAD_TIMEOUT = 60  # seconds
MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
SUPPORTED_REPORT_TYPES = ['morningstar', 'equity_research', 'analyst_report']
DEFAULT_REPORT_TYPE = 'morningstar'

# PDF Extraction Configuration
PDF_EXTRACTION_METHOD = 'pdfplumber'  # Options: 'pdfplumber', 'pypdf2', 'pdfminer'
EXTRACT_IMAGES = False
EXTRACT_TABLES = True
MIN_TEXT_LENGTH = 100  # Minimum characters for valid extraction

# Sentiment Analysis Configuration
SENTIMENT_MODEL = 'finbert'  # Options: 'finbert', 'vader', 'textblob', 'custom'
FINBERT_MODEL_NAME = 'ProsusAI/finbert'
USE_GPU = False  # Set to True if GPU available
BATCH_SIZE = 8
MAX_SEQUENCE_LENGTH = 512

# Sentiment Scoring Thresholds
SENTIMENT_BULLISH_THRESHOLD = 70  # Score >= 70 is bullish
SENTIMENT_BEARISH_THRESHOLD = 30  # Score <= 30 is bearish
CONFIDENCE_HIGH_THRESHOLD = 0.8
CONFIDENCE_MEDIUM_THRESHOLD = 0.6

# Sentiment Categories
SENTIMENT_CATEGORIES = {
    'very_bullish': (85, 100),
    'bullish': (70, 85),
    'neutral': (30, 70),
    'bearish': (15, 30),
    'very_bearish': (0, 15)
}

# Keywords for Financial Sentiment
POSITIVE_KEYWORDS = [
    'strong', 'growth', 'outperform', 'buy', 'upgrade', 'positive',
    'bullish', 'opportunity', 'momentum', 'beat', 'exceed', 'robust',
    'solid', 'impressive', 'accelerating', 'expanding', 'innovative'
]

NEGATIVE_KEYWORDS = [
    'weak', 'decline', 'underperform', 'sell', 'downgrade', 'negative',
    'bearish', 'risk', 'concern', 'miss', 'below', 'disappointing',
    'challenging', 'pressure', 'headwind', 'deteriorating', 'slowing'
]

RISK_KEYWORDS = [
    'risk', 'uncertainty', 'volatile', 'concern', 'challenge', 'threat',
    'competition', 'regulatory', 'litigation', 'debt', 'exposure',
    'vulnerability', 'caution', 'warning', 'adverse'
]

# Metrics Extraction Patterns
PRICE_TARGET_PATTERNS = [
    r'price target[:\s]+\$?(\d+\.?\d*)',
    r'target price[:\s]+\$?(\d+\.?\d*)',
    r'PT[:\s]+\$?(\d+\.?\d*)',
    r'\$(\d+\.?\d*)\s+price target'
]

RATING_PATTERNS = [
    r'rating[:\s]+(buy|hold|sell|outperform|underperform|neutral|overweight|underweight)',
    r'recommendation[:\s]+(buy|hold|sell|outperform|underperform|neutral)',
    r'(buy|hold|sell|outperform|underperform|neutral)\s+rating'
]

EPS_PATTERNS = [
    r'EPS[:\s]+\$?(\d+\.?\d*)',
    r'earnings per share[:\s]+\$?(\d+\.?\d*)',
    r'\$?(\d+\.?\d*)\s+EPS'
]

REVENUE_PATTERNS = [
    r'revenue[:\s]+\$?(\d+\.?\d*)\s*(million|billion|M|B)',
    r'sales[:\s]+\$?(\d+\.?\d*)\s*(million|billion|M|B)'
]

# Rating Mappings
RATING_SCORES = {
    'strong buy': 95,
    'buy': 85,
    'outperform': 75,
    'overweight': 75,
    'accumulate': 70,
    'neutral': 50,
    'hold': 50,
    'market perform': 50,
    'underperform': 25,
    'underweight': 25,
    'reduce': 20,
    'sell': 15,
    'strong sell': 5
}

# Trading Integration Configuration
SENTIMENT_WEIGHT = 0.4  # Weight in combined scoring (40%)
TECHNICAL_WEIGHT = 0.6  # Weight in combined scoring (60%)
MIN_COMBINED_SCORE = 60  # Minimum score for buy signal
MAX_COMBINED_SCORE = 40  # Maximum score for sell signal

# Position Sizing Adjustments
POSITION_MULTIPLIERS = {
    'very_bullish': 1.3,
    'bullish': 1.15,
    'neutral': 1.0,
    'bearish': 0.7,
    'very_bearish': 0.5
}

# Risk Adjustments
RISK_LEVEL_ADJUSTMENTS = {
    'low': 1.1,
    'medium': 1.0,
    'high': 0.8,
    'very_high': 0.6
}

# Report Generation Configuration
REPORT_FORMATS = ['text', 'json', 'html']
DEFAULT_REPORT_FORMAT = 'text'
INCLUDE_CHARTS = True
CHART_DPI = 100

# Historical Tracking
TRACK_SENTIMENT_HISTORY = True
HISTORY_RETENTION_DAYS = 365
SENTIMENT_CHANGE_THRESHOLD = 15  # Alert if sentiment changes by 15+ points

# Alert Configuration
ENABLE_ALERTS = True
ALERT_METHODS = ['console', 'file']  # Options: 'console', 'file', 'email', 'slack'
ALERT_SENTIMENT_CHANGE = 20  # Alert on 20+ point change
ALERT_RATING_CHANGE = True

# Caching Configuration
CACHE_ENABLED = True
CACHE_EXPIRY_HOURS = 24
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# Logging Configuration
LOG_LEVEL = 'INFO'  # Options: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
LOG_FILE = os.path.join(OUTPUT_DIR, 'sentiment_analyzer.log')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Security Configuration
ENCRYPT_CREDENTIALS = True
ENCRYPTION_KEY_FILE = os.path.join(CREDENTIALS_DIR, '.key')
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, 'credentials.enc')

# API Rate Limiting
RATE_LIMIT_REQUESTS = 10  # Max requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

# Batch Processing Configuration
BATCH_PROCESSING_ENABLED = True
MAX_CONCURRENT_DOWNLOADS = 3
BATCH_DELAY_SECONDS = 2  # Delay between batch items

# Model Configuration
FINBERT_CACHE_DIR = os.path.join(MODELS_DIR, 'finbert_cache')
os.makedirs(FINBERT_CACHE_DIR, exist_ok=True)

# Text Processing
MIN_SENTENCE_LENGTH = 10
MAX_SENTENCE_LENGTH = 500
REMOVE_STOPWORDS = False  # Keep stopwords for financial context
LEMMATIZATION = False  # Preserve original financial terms

# Validation
VALIDATE_EXTRACTED_METRICS = True
REQUIRE_PRICE_TARGET = False  # Don't require all metrics
REQUIRE_RATING = False

# Error Handling
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
CONTINUE_ON_ERROR = True  # Continue batch processing on individual errors

# Development/Testing
DEBUG_MODE = False
SAVE_INTERMEDIATE_RESULTS = True
VERBOSE_LOGGING = False

# Version
VERSION = '1.0.0'

# Made with Bob
