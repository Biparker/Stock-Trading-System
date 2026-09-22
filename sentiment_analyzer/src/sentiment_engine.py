"""Sentiment Analysis Engine for analyst reports."""

import os
import re
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import numpy as np
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# FinBERT / transformers import is optional — protobuf version conflicts on some
# environments prevent it from loading. We catch the ImportError and fall back
# gracefully to TextBlob (which gives better financial-domain scores than VADER).
#
# Setting USE_TF=0 before importing transformers prevents it from trying to load
# TensorFlow as a backend. TF 2.21 is compiled against protobuf 6.31.1 and will
# raise a VersionError at runtime when the installed protobuf differs, which
# cascades into a transformers ImportError. PyTorch (USE_PT=1) works fine.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_PT", "1")

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    _TRANSFORMERS_AVAILABLE = True
except Exception:
    _TRANSFORMERS_AVAILABLE = False

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
                if not _TRANSFORMERS_AVAILABLE:
                    raise ImportError(
                        "transformers/torch unavailable due to protobuf conflict"
                    )
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
                logger.warning(f"Unknown model {self.model_name}, defaulting to TextBlob")

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.info("Falling back to TextBlob (financial-domain fallback)")
            # Reset so analyze_text routes to textblob path
            self.model = None
            self.tokenizer = None
            self.vader_analyzer = None
            self.model_name = 'textblob'
    
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

        # FinBERT needs enough tokens to produce a meaningful score.
        # A short sentence (< 40 words) fed to FinBERT often returns near-random
        # probabilities.  Fall through to the faster keyword scorer for short
        # passages so FinBERT is only used on full-paragraph chunks.
        _FINBERT_MIN_WORDS = 40
        text_word_count = len(text.split())

        try:
            if (self.model_name == 'finbert' and self.model is not None
                    and text_word_count >= _FINBERT_MIN_WORDS):
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
        """Split text into sentence-boundary chunks for FinBERT processing.

        Each chunk is guaranteed to contain at least MIN_CHUNK_TOKENS words so
        that FinBERT never receives a fragment too short to score meaningfully
        (avoids the "Text too short for analysis" fallback to neutral).
        """
        MIN_CHUNK_TOKENS = 512  # minimum words per chunk fed to FinBERT

        # Split by sentences
        sentences = re.split(r'[.!?]+', text)

        chunks = []
        current_chunk: List[str] = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_length = len(sentence.split())

            if current_length + sentence_length > max_length:
                if current_chunk:
                    # Only emit chunk if it meets the minimum size threshold
                    if current_length >= MIN_CHUNK_TOKENS:
                        chunks.append(' '.join(current_chunk))
                    else:
                        # Too short — carry sentences into next chunk
                        pass  # current_chunk rolls over below
                current_chunk = current_chunk + [sentence] if current_length < MIN_CHUNK_TOKENS else [sentence]
                current_length = sum(len(s.split()) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        if current_chunk:
            if current_length >= MIN_CHUNK_TOKENS or not chunks:
                # Emit final chunk if it meets threshold, or if it's the only chunk
                chunks.append(' '.join(current_chunk))
            elif chunks:
                # Merge short tail into last chunk rather than scoring it alone
                chunks[-1] = chunks[-1] + ' ' + ' '.join(current_chunk)

        return chunks if chunks else [text]  # never return empty list
    
    def analyze_report(self, pdf_path: str) -> Dict:
        """
        Analyze sentiment of entire analyst report.

        Args:
            pdf_path: Path to PDF report

        Returns:
            dict: Complete sentiment analysis, including report_age_days so
                  MeLLeA can apply the freshness confidence penalty (>90 days → ×0.8).
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

            # ── PDF freshness check ───────────────────────────────────────────
            report_age_days = self._get_report_age_days(pdf_path, text)
            if report_age_days is not None and report_age_days > 90:
                logger.warning(
                    f"Analyst report is {report_age_days} days old (>90) — "
                    "confidence will be reduced by 20% in MeLLeA sentiment stage."
                )

            return {
                'success': True,
                'file_path': pdf_path,
                'analysis_date': datetime.now().isoformat(),
                'overall_sentiment': overall_sentiment,
                'section_sentiments': section_sentiments,
                'key_phrases': phrase_sentiments,
                'risk_assessment': risk_score,
                'extracted_metrics': metrics,
                'report_info': extractor.get_report_info(),
                'report_age_days': report_age_days,
            }

        except Exception as e:
            logger.error(f"Report analysis error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_report_age_days(self, pdf_path: str, text: str) -> Optional[int]:
        """Estimate the age of the analyst report in calendar days.

        Strategy (in order of preference):
        1. Regex-search the first 2000 characters of the extracted text for a
           date pattern (e.g. "August 27, 2025", "2025-08-27", "08/27/2025").
        2. Fall back to the file's mtime if no date is found in the text.
        Returns None if neither succeeds.
        """
        # Common date patterns found in analyst report headers/footers
        date_patterns = [
            r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b',          # 08/27/2025
            r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',          # 2025-08-27
            r'\b(January|February|March|April|May|June|July|August|'
            r'September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
            r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|'
            r'September|October|November|December)\s+(\d{4})\b',
        ]
        month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
        }
        snippet = text[:2000]
        report_date = None

        for pat in date_patterns:
            m = re.search(pat, snippet, re.IGNORECASE)
            if m:
                try:
                    groups = m.groups()
                    if groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                        # numeric patterns
                        if len(groups[0]) == 4:           # YYYY-MM-DD
                            report_date = datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                        elif int(groups[2]) > 31:          # MM/DD/YYYY
                            report_date = datetime(int(groups[2]), int(groups[0]), int(groups[1]))
                    else:
                        # month-name patterns
                        if groups[0].lower() in month_map:  # Month DD, YYYY
                            report_date = datetime(int(groups[2]), month_map[groups[0].lower()], int(groups[1]))
                        elif groups[1].lower() in month_map:  # DD Month YYYY
                            report_date = datetime(int(groups[2]), month_map[groups[1].lower()], int(groups[0]))
                    if report_date:
                        break
                except (ValueError, IndexError):
                    continue

        if report_date is None:
            # Fall back to file modification time
            try:
                mtime = os.path.getmtime(pdf_path)
                report_date = datetime.fromtimestamp(mtime)
            except OSError:
                return None

        age = (datetime.now() - report_date).days
        return max(age, 0)
    
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
    # When called as a subprocess by daily_pipeline.py, emit clean JSON to stdout.
    # Usage: python -m sentiment_analyzer.src.sentiment_engine <path_to_pdf>
    #    or: python sentiment_engine.py <path_to_pdf>  (with sentiment_analyzer/ as cwd)
    import sys, json as _json, pathlib

    # Ensure the sentiment_analyzer package root is importable when run as a script
    _pkg_root = str(pathlib.Path(__file__).parent.parent.parent)
    if _pkg_root not in sys.path:
        sys.path.insert(0, _pkg_root)

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        engine = SentimentEngine(model_name="finbert")
        result = engine.analyze_report(pdf_path)
        print(_json.dumps(result, default=str))
    else:
        print("Usage: python sentiment_engine.py <path_to_pdf>")

# Made with Bob
