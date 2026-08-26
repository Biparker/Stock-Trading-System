"""Sentiment Analysis Engine for analyst reports."""

import os
import re
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from . import config
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


class SentimentEngine:
    """Core sentiment analysis engine for financial text."""
    
    def __init__(self, model_name: str = config.SENTIMENT_MODEL):
        """
        Initialize Sentiment Engine.
        
        Args:
            model_name: Name of sentiment model to use
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.vader_analyzer = None
        
        self._load_model()
        logger.info(f"SentimentEngine initialized with model: {model_name}")
    
    def _load_model(self):
        """Load the sentiment analysis model."""
        try:
            if self.model_name == 'finbert':
                logger.info("Loading FinBERT model...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    config.FINBERT_MODEL_NAME,
                    cache_dir=config.FINBERT_CACHE_DIR
                )
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    config.FINBERT_MODEL_NAME,
                    cache_dir=config.FINBERT_CACHE_DIR
                )
                
                # Move to GPU if available and configured
                if config.USE_GPU and torch.cuda.is_available():
                    self.model = self.model.cuda()
                    logger.info("Model loaded on GPU")
                else:
                    logger.info("Model loaded on CPU")
                    
            elif self.model_name == 'vader':
                logger.info("Loading VADER analyzer...")
                self.vader_analyzer = SentimentIntensityAnalyzer()
                
            elif self.model_name == 'textblob':
                logger.info("Using TextBlob for sentiment analysis")
                # TextBlob doesn't require loading
                pass
                
            else:
                logger.warning(f"Unknown model {self.model_name}, defaulting to VADER")
                self.vader_analyzer = SentimentIntensityAnalyzer()
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.info("Falling back to VADER")
            self.vader_analyzer = SentimentIntensityAnalyzer()
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
        
        Returns:
            dict: Sentiment analysis results
        """
        if not text or len(text) < config.MIN_TEXT_LENGTH:
            logger.warning("Text too short for analysis")
            return {
                'sentiment_score': 50,
                'sentiment_label': 'neutral',
                'confidence': 0.0,
                'method': 'none'
            }
        
        try:
            if self.model_name == 'finbert' and self.model is not None:
                return self._analyze_with_finbert(text)
            elif self.model_name == 'vader' or self.vader_analyzer is not None:
                return self._analyze_with_vader(text)
            elif self.model_name == 'textblob':
                return self._analyze_with_textblob(text)
            else:
                return self._analyze_with_keywords(text)
                
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return self._analyze_with_keywords(text)
    
    def _analyze_with_finbert(self, text: str) -> Dict:
        """Analyze sentiment using FinBERT model."""
        try:
            # Split text into chunks if too long
            max_length = config.MAX_SEQUENCE_LENGTH
            chunks = self._split_text(text, max_length)
            
            all_scores = []
            all_labels = []
            
            for chunk in chunks:
                # Tokenize
                inputs = self.tokenizer(
                    chunk,
                    return_tensors="pt",
                    truncation=True,
                    max_length=max_length,
                    padding=True
                )
                
                # Move to GPU if available
                if config.USE_GPU and torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}
                
                # Get predictions
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                
                # FinBERT outputs: [negative, neutral, positive]
                probs = predictions[0].cpu().numpy()
                
                # Convert to 0-100 scale
                # Weighted: negative=-1, neutral=0, positive=1
                sentiment_value = (probs[2] - probs[0]) * 50 + 50
                
                all_scores.append(sentiment_value)
                all_labels.append(probs)
            
            # Average across chunks
            avg_score = np.mean(all_scores)
            avg_probs = np.mean(all_labels, axis=0)
            
            # Determine label
            if avg_score >= config.SENTIMENT_BULLISH_THRESHOLD:
                label = 'bullish'
            elif avg_score <= config.SENTIMENT_BEARISH_THRESHOLD:
                label = 'bearish'
            else:
                label = 'neutral'
            
            # Confidence is the max probability
            confidence = float(np.max(avg_probs))
            
            return {
                'sentiment_score': float(avg_score),
                'sentiment_label': label,
                'confidence': confidence,
                'method': 'finbert',
                'probabilities': {
                    'negative': float(avg_probs[0]),
                    'neutral': float(avg_probs[1]),
                    'positive': float(avg_probs[2])
                }
            }
            
        except Exception as e:
            logger.error(f"FinBERT analysis error: {e}")
            return self._analyze_with_vader(text)
    
    def _analyze_with_vader(self, text: str) -> Dict:
        """Analyze sentiment using VADER."""
        try:
            scores = self.vader_analyzer.polarity_scores(text)
            
            # Convert compound score (-1 to 1) to 0-100 scale
            sentiment_score = (scores['compound'] + 1) * 50
            
            # Determine label
            if sentiment_score >= config.SENTIMENT_BULLISH_THRESHOLD:
                label = 'bullish'
            elif sentiment_score <= config.SENTIMENT_BEARISH_THRESHOLD:
                label = 'bearish'
            else:
                label = 'neutral'
            
            # Confidence based on how far from neutral
            confidence = abs(scores['compound'])
            
            return {
                'sentiment_score': float(sentiment_score),
                'sentiment_label': label,
                'confidence': float(confidence),
                'method': 'vader',
                'scores': {
                    'negative': scores['neg'],
                    'neutral': scores['neu'],
                    'positive': scores['pos'],
                    'compound': scores['compound']
                }
            }
            
        except Exception as e:
            logger.error(f"VADER analysis error: {e}")
            return self._analyze_with_keywords(text)
    
    def _analyze_with_textblob(self, text: str) -> Dict:
        """Analyze sentiment using TextBlob."""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            
            # Convert to 0-100 scale
            sentiment_score = (polarity + 1) * 50
            
            # Determine label
            if sentiment_score >= config.SENTIMENT_BULLISH_THRESHOLD:
                label = 'bullish'
            elif sentiment_score <= config.SENTIMENT_BEARISH_THRESHOLD:
                label = 'bearish'
            else:
                label = 'neutral'
            
            confidence = abs(polarity)
            
            return {
                'sentiment_score': float(sentiment_score),
                'sentiment_label': label,
                'confidence': float(confidence),
                'method': 'textblob',
                'polarity': float(polarity),
                'subjectivity': float(blob.sentiment.subjectivity)
            }
            
        except Exception as e:
            logger.error(f"TextBlob analysis error: {e}")
            return self._analyze_with_keywords(text)
    
    def _analyze_with_keywords(self, text: str) -> Dict:
        """Fallback keyword-based sentiment analysis."""
        text_lower = text.lower()
        
        # Count positive and negative keywords
        positive_count = sum(1 for keyword in config.POSITIVE_KEYWORDS 
                           if keyword in text_lower)
        negative_count = sum(1 for keyword in config.NEGATIVE_KEYWORDS 
                           if keyword in text_lower)
        
        total_keywords = positive_count + negative_count
        
        if total_keywords == 0:
            sentiment_score = 50.0
            confidence = 0.0
        else:
            # Calculate score based on ratio
            sentiment_score = (positive_count / total_keywords) * 100
            confidence = min(total_keywords / 20, 1.0)  # Max confidence at 20 keywords
        
        # Determine label
        if sentiment_score >= config.SENTIMENT_BULLISH_THRESHOLD:
            label = 'bullish'
        elif sentiment_score <= config.SENTIMENT_BEARISH_THRESHOLD:
            label = 'bearish'
        else:
            label = 'neutral'
        
        return {
            'sentiment_score': float(sentiment_score),
            'sentiment_label': label,
            'confidence': float(confidence),
            'method': 'keywords',
            'positive_keywords': positive_count,
            'negative_keywords': negative_count
        }
    
    def _split_text(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks for processing."""
        # Split by sentences
        sentences = re.split(r'[.!?]+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > max_length:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def analyze_report(self, pdf_path: str) -> Dict:
        """
        Analyze sentiment of entire analyst report.
        
        Args:
            pdf_path: Path to PDF report
        
        Returns:
            dict: Complete sentiment analysis
        """
        logger.info(f"Analyzing report: {pdf_path}")
        
        try:
            # Extract text from PDF
            extractor = PDFExtractor(pdf_path)
            extraction_result = extractor.extract()
            
            if not extraction_result['success']:
                logger.error("PDF extraction failed")
                return {
                    'success': False,
                    'error': 'PDF extraction failed'
                }
            
            text = extraction_result['text']
            
            # Overall sentiment
            overall_sentiment = self.analyze_text(text)
            
            # Section-based sentiment
            sections = extractor.extract_sections()
            section_sentiments = {}
            
            for section_name, section_text in sections.items():
                if section_text:
                    section_sentiments[section_name] = self.analyze_text(section_text)
            
            # Extract key phrases with sentiment
            key_phrases = extractor.extract_key_phrases()
            phrase_sentiments = []
            
            for phrase in key_phrases[:10]:  # Top 10 phrases
                sentiment = self.analyze_text(phrase)
                phrase_sentiments.append({
                    'phrase': phrase,
                    'sentiment': sentiment
                })
            
            # Risk assessment
            risk_score = self._assess_risk(text)
            
            # Extract metrics
            metrics = self._extract_metrics(text)
            
            return {
                'success': True,
                'file_path': pdf_path,
                'analysis_date': datetime.now().isoformat(),
                'overall_sentiment': overall_sentiment,
                'section_sentiments': section_sentiments,
                'key_phrases': phrase_sentiments,
                'risk_assessment': risk_score,
                'extracted_metrics': metrics,
                'report_info': extractor.get_report_info()
            }
            
        except Exception as e:
            logger.error(f"Report analysis error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _assess_risk(self, text: str) -> Dict:
        """Assess risk level from text."""
        text_lower = text.lower()
        
        # Count risk keywords
        risk_count = sum(1 for keyword in config.RISK_KEYWORDS 
                        if keyword in text_lower)
        
        # Determine risk level
        if risk_count >= 10:
            risk_level = 'very_high'
        elif risk_count >= 7:
            risk_level = 'high'
        elif risk_count >= 4:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'risk_mentions': risk_count,
            'risk_adjustment': config.RISK_LEVEL_ADJUSTMENTS.get(risk_level, 1.0)
        }
    
    def _extract_metrics(self, text: str) -> Dict:
        """Extract financial metrics from text."""
        metrics = {}
        
        # Price target
        for pattern in config.PRICE_TARGET_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    metrics['price_target'] = float(match.group(1))
                    break
                except:
                    pass
        
        # Rating
        for pattern in config.RATING_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rating = match.group(1).lower()
                metrics['rating'] = rating
                metrics['rating_score'] = config.RATING_SCORES.get(rating, 50)
                break
        
        # EPS
        for pattern in config.EPS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    metrics['eps_estimate'] = float(match.group(1))
                    break
                except:
                    pass
        
        return metrics


if __name__ == "__main__":
    # Test the engine
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        engine = SentimentEngine()
        result = engine.analyze_report(pdf_path)
        
        print(f"\n=== Sentiment Analysis Results ===")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"\nOverall Sentiment:")
            print(f"  Score: {result['overall_sentiment']['sentiment_score']:.2f}")
            print(f"  Label: {result['overall_sentiment']['sentiment_label']}")
            print(f"  Confidence: {result['overall_sentiment']['confidence']:.2f}")
            print(f"  Method: {result['overall_sentiment']['method']}")
    else:
        print("Usage: python sentiment_engine.py <path_to_pdf>")

# Made with Bob
