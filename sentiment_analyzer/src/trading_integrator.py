"""Trading Integration Agent for incorporating sentiment into trading decisions."""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from . import config
from .sentiment_engine import SentimentEngine

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingIntegrator:
    """Integrate sentiment analysis with trading system decisions."""
    
    def __init__(self):
        """Initialize Trading Integrator."""
        self.sentiment_engine = SentimentEngine()
        self.sentiment_cache = {}
        logger.info("TradingIntegrator initialized")
    
    def get_sentiment_score(
        self,
        ticker: str,
        pdf_path: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Get sentiment score for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            pdf_path: Path to analyst report PDF (optional)
            use_cache: Whether to use cached results
        
        Returns:
            dict: Sentiment score and metadata
        """
        # Check cache first
        if use_cache and ticker in self.sentiment_cache:
            cached = self.sentiment_cache[ticker]
            cache_age = datetime.now() - datetime.fromisoformat(cached['timestamp'])
            
            if cache_age < timedelta(hours=config.CACHE_EXPIRY_HOURS):
                logger.info(f"Using cached sentiment for {ticker}")
                return cached
        
        # Analyze report
        if pdf_path is None:
            # Look for most recent report
            pdf_path = self._find_latest_report(ticker)
        
        if pdf_path is None:
            logger.warning(f"No report found for {ticker}")
            return {
                'ticker': ticker,
                'sentiment_score': 50.0,
                'sentiment_label': 'neutral',
                'confidence': 0.0,
                'available': False,
                'timestamp': datetime.now().isoformat()
            }
        
        # Perform analysis
        result = self.sentiment_engine.analyze_report(pdf_path)
        
        if not result['success']:
            logger.error(f"Sentiment analysis failed for {ticker}")
            return {
                'ticker': ticker,
                'sentiment_score': 50.0,
                'sentiment_label': 'neutral',
                'confidence': 0.0,
                'available': False,
                'error': result.get('error', 'Unknown error'),
                'timestamp': datetime.now().isoformat()
            }
        
        # Extract key information
        sentiment_data = {
            'ticker': ticker,
            'sentiment_score': result['overall_sentiment']['sentiment_score'],
            'sentiment_label': result['overall_sentiment']['sentiment_label'],
            'confidence': result['overall_sentiment']['confidence'],
            'method': result['overall_sentiment']['method'],
            'risk_level': result.get('risk_assessment', {}).get('risk_level', 'medium'),
            'risk_adjustment': result.get('risk_assessment', {}).get('risk_adjustment', 1.0),
            'extracted_metrics': result.get('extracted_metrics', {}),
            'available': True,
            'timestamp': datetime.now().isoformat(),
            'report_path': pdf_path
        }
        
        # Cache result
        if config.CACHE_ENABLED:
            self.sentiment_cache[ticker] = sentiment_data
        
        return sentiment_data
    
    def _find_latest_report(self, ticker: str) -> Optional[str]:
        """Find the most recent report for a ticker."""
        if not os.path.exists(config.SAMPLE_REPORTS_DIR):
            return None
        
        # Look for files matching ticker
        matching_files = []
        for filename in os.listdir(config.SAMPLE_REPORTS_DIR):
            if ticker.upper() in filename.upper() and filename.endswith('.pdf'):
                file_path = os.path.join(config.SAMPLE_REPORTS_DIR, filename)
                matching_files.append((file_path, os.path.getmtime(file_path)))
        
        if not matching_files:
            return None
        
        # Return most recent
        latest_file = max(matching_files, key=lambda x: x[1])
        return latest_file[0]
    
    def generate_combined_score(
        self,
        ticker: str,
        technical_score: float,
        pdf_path: Optional[str] = None
    ) -> Dict:
        """
        Generate combined score from technical analysis and sentiment.
        
        Args:
            ticker: Stock ticker symbol
            technical_score: Technical analysis score (0-100)
            pdf_path: Path to analyst report PDF (optional)
        
        Returns:
            dict: Combined scoring and recommendation
        """
        # Get sentiment score
        sentiment_data = self.get_sentiment_score(ticker, pdf_path)
        
        if not sentiment_data['available']:
            logger.warning(f"Sentiment not available for {ticker}, using technical only")
            return {
                'ticker': ticker,
                'combined_score': technical_score,
                'technical_score': technical_score,
                'sentiment_score': 50.0,
                'sentiment_weight': 0.0,
                'technical_weight': 1.0,
                'recommendation': self._score_to_recommendation(technical_score),
                'sentiment_available': False
            }
        
        # Calculate weighted combined score
        sentiment_score = sentiment_data['sentiment_score']
        combined_score = (
            technical_score * config.TECHNICAL_WEIGHT +
            sentiment_score * config.SENTIMENT_WEIGHT
        )
        
        # Adjust for risk
        risk_adjustment = sentiment_data.get('risk_adjustment', 1.0)
        adjusted_score = combined_score * risk_adjustment
        
        # Generate recommendation
        recommendation = self._score_to_recommendation(adjusted_score)
        
        # Calculate position size multiplier
        position_multiplier = self._calculate_position_multiplier(
            sentiment_data['sentiment_label'],
            sentiment_data['risk_level'],
            sentiment_data['confidence']
        )
        
        return {
            'ticker': ticker,
            'combined_score': adjusted_score,
            'raw_combined_score': combined_score,
            'technical_score': technical_score,
            'sentiment_score': sentiment_score,
            'sentiment_weight': config.SENTIMENT_WEIGHT,
            'technical_weight': config.TECHNICAL_WEIGHT,
            'risk_adjustment': risk_adjustment,
            'recommendation': recommendation,
            'position_multiplier': position_multiplier,
            'sentiment_label': sentiment_data['sentiment_label'],
            'sentiment_confidence': sentiment_data['confidence'],
            'risk_level': sentiment_data['risk_level'],
            'sentiment_available': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def _score_to_recommendation(self, score: float) -> str:
        """Convert score to trading recommendation."""
        if score >= 75:
            return 'STRONG BUY'
        elif score >= config.MIN_COMBINED_SCORE:
            return 'BUY'
        elif score >= 50:
            return 'HOLD'
        elif score >= config.MAX_COMBINED_SCORE:
            return 'REDUCE'
        else:
            return 'SELL'
    
    def _calculate_position_multiplier(
        self,
        sentiment_label: str,
        risk_level: str,
        confidence: float
    ) -> float:
        """Calculate position size multiplier based on sentiment and risk."""
        # Base multiplier from sentiment
        if sentiment_label == 'very_bullish':
            base_multiplier = 1.3
        elif sentiment_label == 'bullish':
            base_multiplier = 1.15
        elif sentiment_label == 'neutral':
            base_multiplier = 1.0
        elif sentiment_label == 'bearish':
            base_multiplier = 0.7
        else:  # very_bearish
            base_multiplier = 0.5
        
        # Adjust for risk
        risk_multiplier = config.RISK_LEVEL_ADJUSTMENTS.get(risk_level, 1.0)
        
        # Adjust for confidence
        confidence_multiplier = 0.8 + (confidence * 0.4)  # Range: 0.8 to 1.2
        
        # Combined multiplier
        final_multiplier = base_multiplier * risk_multiplier * confidence_multiplier
        
        # Clamp to reasonable range
        return max(0.3, min(1.5, final_multiplier))
    
    def generate_trading_signal(
        self,
        ticker: str,
        technical_score: float,
        current_price: float,
        pdf_path: Optional[str] = None
    ) -> Dict:
        """
        Generate complete trading signal with sentiment integration.
        
        Args:
            ticker: Stock ticker symbol
            technical_score: Technical analysis score (0-100)
            current_price: Current stock price
            pdf_path: Path to analyst report PDF (optional)
        
        Returns:
            dict: Complete trading signal
        """
        # Get combined score
        combined = self.generate_combined_score(ticker, technical_score, pdf_path)
        
        # Get sentiment data for additional context
        sentiment_data = self.get_sentiment_score(ticker, pdf_path)
        
        # Extract price target if available
        price_target = None
        upside_potential = None
        
        if sentiment_data.get('extracted_metrics'):
            price_target = sentiment_data['extracted_metrics'].get('price_target')
            if price_target:
                upside_potential = ((price_target - current_price) / current_price) * 100
        
        # Generate signal
        signal = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'current_price': current_price,
            'price_target': price_target,
            'upside_potential_pct': upside_potential,
            'recommendation': combined['recommendation'],
            'combined_score': combined['combined_score'],
            'technical_score': combined['technical_score'],
            'sentiment_score': combined['sentiment_score'],
            'position_multiplier': combined['position_multiplier'],
            'sentiment_label': combined.get('sentiment_label', 'neutral'),
            'sentiment_confidence': combined.get('sentiment_confidence', 0.0),
            'risk_level': combined.get('risk_level', 'medium'),
            'sentiment_available': combined['sentiment_available']
        }
        
        # Add rationale
        signal['rationale'] = self._generate_rationale(signal)
        
        # Save signal
        self._save_trading_signal(signal)
        
        return signal
    
    def _generate_rationale(self, signal: Dict) -> str:
        """Generate human-readable rationale for trading signal."""
        parts = []
        
        # Overall recommendation
        parts.append(f"Recommendation: {signal['recommendation']}")
        
        # Score breakdown
        parts.append(
            f"Combined score of {signal['combined_score']:.1f} "
            f"(Technical: {signal['technical_score']:.1f}, "
            f"Sentiment: {signal['sentiment_score']:.1f})"
        )
        
        # Sentiment context
        if signal['sentiment_available']:
            parts.append(
                f"Analyst sentiment is {signal['sentiment_label']} "
                f"with {signal['sentiment_confidence']:.0%} confidence"
            )
        
        # Price target
        if signal.get('upside_potential_pct'):
            parts.append(
                f"Price target implies {signal['upside_potential_pct']:.1f}% "
                f"{'upside' if signal['upside_potential_pct'] > 0 else 'downside'}"
            )
        
        # Risk
        parts.append(f"Risk level: {signal['risk_level']}")
        
        # Position sizing
        parts.append(
            f"Suggested position size multiplier: {signal['position_multiplier']:.2f}x"
        )
        
        return ". ".join(parts) + "."
    
    def _save_trading_signal(self, signal: Dict):
        """Save trading signal to file."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{signal['ticker']}_signal_{timestamp}.json"
            filepath = os.path.join(config.TRADING_SIGNALS_DIR, filename)
            
            with open(filepath, 'w') as f:
                json.dump(signal, f, indent=2, default=str)
            
            logger.info(f"Trading signal saved: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving trading signal: {e}")
    
    def batch_generate_signals(
        self,
        tickers_with_scores: List[Tuple[str, float, float]]
    ) -> Dict[str, Dict]:
        """
        Generate trading signals for multiple tickers.
        
        Args:
            tickers_with_scores: List of (ticker, technical_score, current_price) tuples
        
        Returns:
            dict: Mapping of ticker to trading signal
        """
        signals = {}
        
        for ticker, technical_score, current_price in tickers_with_scores:
            logger.info(f"Generating signal for {ticker}")
            
            try:
                signal = self.generate_trading_signal(
                    ticker,
                    technical_score,
                    current_price
                )
                signals[ticker] = signal
                
            except Exception as e:
                logger.error(f"Error generating signal for {ticker}: {e}")
                signals[ticker] = {
                    'ticker': ticker,
                    'error': str(e),
                    'recommendation': 'ERROR'
                }
        
        return signals
    
    def get_sentiment_history(self, ticker: str, days: int = 90) -> List[Dict]:
        """
        Get historical sentiment data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back
        
        Returns:
            list: Historical sentiment records
        """
        history = []
        
        if not os.path.exists(config.SENTIMENT_REPORTS_DIR):
            return history
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Look for historical reports
        for filename in os.listdir(config.SENTIMENT_REPORTS_DIR):
            if ticker.upper() in filename.upper() and filename.endswith('.json'):
                filepath = os.path.join(config.SENTIMENT_REPORTS_DIR, filename)
                
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    # Check if within date range
                    report_date = datetime.fromisoformat(data.get('analysis_date', ''))
                    if report_date >= cutoff_date:
                        history.append({
                            'date': data['analysis_date'],
                            'sentiment_score': data['overall_sentiment']['sentiment_score'],
                            'sentiment_label': data['overall_sentiment']['sentiment_label'],
                            'confidence': data['overall_sentiment']['confidence']
                        })
                        
                except Exception as e:
                    logger.error(f"Error reading historical report {filename}: {e}")
        
        # Sort by date
        history.sort(key=lambda x: x['date'])
        
        return history
    
    def detect_sentiment_change(
        self,
        ticker: str,
        current_sentiment: float,
        threshold: float = config.SENTIMENT_CHANGE_THRESHOLD
    ) -> Optional[Dict]:
        """
        Detect significant sentiment changes.
        
        Args:
            ticker: Stock ticker symbol
            current_sentiment: Current sentiment score
            threshold: Minimum change to trigger alert
        
        Returns:
            dict: Alert information if change detected, None otherwise
        """
        history = self.get_sentiment_history(ticker, days=30)
        
        if not history:
            return None
        
        # Get most recent historical sentiment
        previous_sentiment = history[-1]['sentiment_score']
        
        # Calculate change
        change = current_sentiment - previous_sentiment
        
        if abs(change) >= threshold:
            return {
                'ticker': ticker,
                'alert_type': 'sentiment_change',
                'previous_sentiment': previous_sentiment,
                'current_sentiment': current_sentiment,
                'change': change,
                'change_pct': (change / previous_sentiment) * 100 if previous_sentiment != 0 else 0,
                'direction': 'improved' if change > 0 else 'deteriorated',
                'timestamp': datetime.now().isoformat()
            }
        
        return None


if __name__ == "__main__":
    # Test the integrator
    integrator = TradingIntegrator()
    
    # Test signal generation
    signal = integrator.generate_trading_signal(
        ticker='AAPL',
        technical_score=72.5,
        current_price=150.00
    )
    
    print("\n=== Trading Signal ===")
    print(json.dumps(signal, indent=2, default=str))

# Made with Bob
