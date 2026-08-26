"""Report Generator for sentiment analysis results."""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from . import config

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate comprehensive sentiment analysis reports."""
    
    def __init__(self):
        """Initialize Report Generator."""
        logger.info("ReportGenerator initialized")
    
    def generate_report(
        self,
        analysis_result: Dict,
        output_format: str = config.DEFAULT_REPORT_FORMAT,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate sentiment analysis report.
        
        Args:
            analysis_result: Sentiment analysis results
            output_format: Report format ('text', 'json', 'html')
            output_path: Custom output path (optional)
        
        Returns:
            str: Path to generated report
        """
        if not analysis_result.get('success'):
            logger.error("Cannot generate report from failed analysis")
            return ""
        
        try:
            if output_format == 'text':
                return self._generate_text_report(analysis_result, output_path)
            elif output_format == 'json':
                return self._generate_json_report(analysis_result, output_path)
            elif output_format == 'html':
                return self._generate_html_report(analysis_result, output_path)
            else:
                logger.warning(f"Unknown format {output_format}, using text")
                return self._generate_text_report(analysis_result, output_path)
                
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return ""
    
    def _generate_text_report(self, result: Dict, output_path: Optional[str]) -> str:
        """Generate text format report."""
        ticker = result.get('report_info', {}).get('ticker', 'UNKNOWN')
        
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                config.SENTIMENT_REPORTS_DIR,
                f"{ticker}_sentiment_report_{timestamp}.txt"
            )
        
        lines = []
        lines.append("=" * 80)
        lines.append("STOCK SENTIMENT ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Executive Summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        overall = result['overall_sentiment']
        lines.append(f"Ticker Symbol: {ticker}")
        lines.append(f"Analysis Date: {result['analysis_date']}")
        lines.append(f"Report File: {os.path.basename(result['file_path'])}")
        lines.append("")
        lines.append(f"Overall Sentiment Score: {overall['sentiment_score']:.2f} / 100")
        lines.append(f"Sentiment Classification: {overall['sentiment_label'].upper()}")
        lines.append(f"Confidence Level: {overall['confidence']:.2%}")
        lines.append(f"Analysis Method: {overall['method'].upper()}")
        lines.append("")
        
        # Sentiment Category
        category = self._get_sentiment_category(overall['sentiment_score'])
        lines.append(f"Sentiment Category: {category.replace('_', ' ').title()}")
        lines.append("")
        
        # Extracted Metrics
        if result.get('extracted_metrics'):
            lines.append("EXTRACTED METRICS")
            lines.append("-" * 80)
            metrics = result['extracted_metrics']
            
            if 'price_target' in metrics:
                lines.append(f"Price Target: ${metrics['price_target']:.2f}")
            
            if 'rating' in metrics:
                lines.append(f"Analyst Rating: {metrics['rating'].title()}")
                lines.append(f"Rating Score: {metrics.get('rating_score', 'N/A')}")
            
            if 'eps_estimate' in metrics:
                lines.append(f"EPS Estimate: ${metrics['eps_estimate']:.2f}")
            
            lines.append("")
        
        # Risk Assessment
        if result.get('risk_assessment'):
            lines.append("RISK ASSESSMENT")
            lines.append("-" * 80)
            risk = result['risk_assessment']
            lines.append(f"Risk Level: {risk['risk_level'].replace('_', ' ').title()}")
            lines.append(f"Risk Mentions: {risk['risk_mentions']}")
            lines.append(f"Risk Adjustment Factor: {risk['risk_adjustment']:.2f}")
            lines.append("")
        
        # Section Sentiments
        if result.get('section_sentiments'):
            lines.append("SECTION-BY-SECTION SENTIMENT")
            lines.append("-" * 80)
            
            for section_name, sentiment in result['section_sentiments'].items():
                lines.append(f"\n{section_name.replace('_', ' ').title()}:")
                lines.append(f"  Score: {sentiment['sentiment_score']:.2f}")
                lines.append(f"  Label: {sentiment['sentiment_label'].title()}")
                lines.append(f"  Confidence: {sentiment['confidence']:.2%}")
            
            lines.append("")
        
        # Key Phrases
        if result.get('key_phrases'):
            lines.append("KEY PHRASES WITH SENTIMENT")
            lines.append("-" * 80)
            
            for i, phrase_data in enumerate(result['key_phrases'][:5], 1):
                phrase = phrase_data['phrase']
                sentiment = phrase_data['sentiment']
                
                # Truncate long phrases
                if len(phrase) > 100:
                    phrase = phrase[:97] + "..."
                
                lines.append(f"\n{i}. {phrase}")
                lines.append(f"   Sentiment: {sentiment['sentiment_label'].title()} "
                           f"({sentiment['sentiment_score']:.1f})")
            
            lines.append("")
        
        # Trading Recommendation
        lines.append("TRADING RECOMMENDATION")
        lines.append("-" * 80)
        recommendation = self._generate_recommendation(result)
        lines.append(f"Recommended Action: {recommendation['action'].upper()}")
        lines.append(f"Position Size Multiplier: {recommendation['position_multiplier']:.2f}")
        lines.append(f"Rationale: {recommendation['rationale']}")
        lines.append("")
        
        # Disclaimers
        lines.append("IMPORTANT DISCLAIMERS")
        lines.append("-" * 80)
        lines.append("• This analysis is for informational purposes only")
        lines.append("• Sentiment analysis is one factor among many in investment decisions")
        lines.append("• Past analyst opinions do not guarantee future performance")
        lines.append("• Always conduct your own due diligence")
        lines.append("• Consult with a financial advisor before making investment decisions")
        lines.append("• The authors assume no liability for any financial losses")
        lines.append("")
        lines.append("=" * 80)
        lines.append(f"Report generated by B. I. Parker Data Science and Consulting LLC")
        lines.append(f"Sentiment Analyzer v{config.VERSION}")
        lines.append("=" * 80)
        
        # Write to file
        report_text = '\n'.join(lines)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"Text report generated: {output_path}")
        return output_path
    
    def _generate_json_report(self, result: Dict, output_path: Optional[str]) -> str:
        """Generate JSON format report."""
        ticker = result.get('report_info', {}).get('ticker', 'UNKNOWN')
        
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                config.SENTIMENT_REPORTS_DIR,
                f"{ticker}_sentiment_report_{timestamp}.json"
            )
        
        # Add recommendation to result
        result['trading_recommendation'] = self._generate_recommendation(result)
        result['sentiment_category'] = self._get_sentiment_category(
            result['overall_sentiment']['sentiment_score']
        )
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, default=str)
        
        logger.info(f"JSON report generated: {output_path}")
        return output_path
    
    def _generate_html_report(self, result: Dict, output_path: Optional[str]) -> str:
        """Generate HTML format report."""
        ticker = result.get('report_info', {}).get('ticker', 'UNKNOWN')
        
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                config.SENTIMENT_REPORTS_DIR,
                f"{ticker}_sentiment_report_{timestamp}.html"
            )
        
        overall = result['overall_sentiment']
        category = self._get_sentiment_category(overall['sentiment_score'])
        recommendation = self._generate_recommendation(result)
        
        # Generate HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sentiment Analysis Report - {ticker}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background-color: white; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
        .metric {{ background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .metric-label {{ font-weight: bold; color: #7f8c8d; }}
        .metric-value {{ font-size: 1.2em; color: #2c3e50; }}
        .sentiment-score {{ font-size: 2em; font-weight: bold; text-align: center; padding: 20px; margin: 20px 0; border-radius: 10px; }}
        .bullish {{ background-color: #d4edda; color: #155724; }}
        .bearish {{ background-color: #f8d7da; color: #721c24; }}
        .neutral {{ background-color: #fff3cd; color: #856404; }}
        .disclaimer {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #3498db; color: white; }}
        .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #bdc3c7; color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Stock Sentiment Analysis Report</h1>
        
        <div class="metric">
            <span class="metric-label">Ticker Symbol:</span>
            <span class="metric-value">{ticker}</span>
        </div>
        
        <div class="metric">
            <span class="metric-label">Analysis Date:</span>
            <span class="metric-value">{result['analysis_date']}</span>
        </div>
        
        <div class="sentiment-score {overall['sentiment_label']}">
            Sentiment Score: {overall['sentiment_score']:.2f} / 100<br>
            <span style="font-size: 0.6em;">{category.replace('_', ' ').title()}</span>
        </div>
        
        <h2>Overall Sentiment</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Classification</td>
                <td>{overall['sentiment_label'].upper()}</td>
            </tr>
            <tr>
                <td>Confidence</td>
                <td>{overall['confidence']:.2%}</td>
            </tr>
            <tr>
                <td>Analysis Method</td>
                <td>{overall['method'].upper()}</td>
            </tr>
        </table>
        
        <h2>Trading Recommendation</h2>
        <div class="metric">
            <span class="metric-label">Recommended Action:</span>
            <span class="metric-value">{recommendation['action'].upper()}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Position Size Multiplier:</span>
            <span class="metric-value">{recommendation['position_multiplier']:.2f}</span>
        </div>
        <p>{recommendation['rationale']}</p>
        
        <div class="disclaimer">
            <strong>⚠️ Important Disclaimers:</strong><br>
            This analysis is for informational purposes only. Sentiment analysis is one factor among many in investment decisions.
            Always conduct your own due diligence and consult with a financial advisor before making investment decisions.
        </div>
        
        <div class="footer">
            Report generated by B. I. Parker Data Science and Consulting LLC<br>
            Sentiment Analyzer v{config.VERSION}
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"HTML report generated: {output_path}")
        return output_path
    
    def _get_sentiment_category(self, score: float) -> str:
        """Get sentiment category from score."""
        for category, (min_score, max_score) in config.SENTIMENT_CATEGORIES.items():
            if min_score <= score <= max_score:
                return category
        return 'neutral'
    
    def _generate_recommendation(self, result: Dict) -> Dict:
        """Generate trading recommendation based on sentiment."""
        sentiment_score = result['overall_sentiment']['sentiment_score']
        category = self._get_sentiment_category(sentiment_score)
        
        # Get position multiplier
        position_multiplier = config.POSITION_MULTIPLIERS.get(category, 1.0)
        
        # Adjust for risk
        if result.get('risk_assessment'):
            risk_adjustment = result['risk_assessment']['risk_adjustment']
            position_multiplier *= risk_adjustment
        
        # Determine action
        if sentiment_score >= 70:
            action = 'buy'
            rationale = f"Strong positive sentiment ({sentiment_score:.1f}) suggests favorable outlook."
        elif sentiment_score >= 55:
            action = 'hold/accumulate'
            rationale = f"Moderately positive sentiment ({sentiment_score:.1f}) supports holding or gradual accumulation."
        elif sentiment_score >= 45:
            action = 'hold'
            rationale = f"Neutral sentiment ({sentiment_score:.1f}) suggests maintaining current position."
        elif sentiment_score >= 30:
            action = 'reduce'
            rationale = f"Moderately negative sentiment ({sentiment_score:.1f}) suggests reducing exposure."
        else:
            action = 'sell/avoid'
            rationale = f"Strong negative sentiment ({sentiment_score:.1f}) suggests avoiding or exiting position."
        
        return {
            'action': action,
            'position_multiplier': position_multiplier,
            'sentiment_score': sentiment_score,
            'sentiment_category': category,
            'rationale': rationale
        }
    
    def generate_visualization(self, result: Dict, output_path: Optional[str] = None) -> str:
        """
        Generate sentiment visualization chart.
        
        Args:
            result: Sentiment analysis results
            output_path: Custom output path (optional)
        
        Returns:
            str: Path to generated chart
        """
        if not config.INCLUDE_CHARTS:
            return ""
        
        ticker = result.get('report_info', {}).get('ticker', 'UNKNOWN')
        
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                config.SENTIMENT_REPORTS_DIR,
                f"{ticker}_sentiment_chart_{timestamp}.png"
            )
        
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            # Overall sentiment gauge
            score = result['overall_sentiment']['sentiment_score']
            
            ax1.barh(['Sentiment'], [score], color=self._get_color(score))
            ax1.set_xlim(0, 100)
            ax1.set_xlabel('Sentiment Score')
            ax1.set_title(f'{ticker} Overall Sentiment')
            ax1.axvline(x=50, color='gray', linestyle='--', alpha=0.5)
            
            # Add score text
            ax1.text(score, 0, f'{score:.1f}', ha='center', va='center', 
                    fontsize=12, fontweight='bold')
            
            # Section sentiments
            if result.get('section_sentiments'):
                sections = list(result['section_sentiments'].keys())
                scores = [result['section_sentiments'][s]['sentiment_score'] 
                         for s in sections]
                colors = [self._get_color(s) for s in scores]
                
                y_pos = range(len(sections))
                ax2.barh(y_pos, scores, color=colors)
                ax2.set_yticks(y_pos)
                ax2.set_yticklabels([s.replace('_', ' ').title() for s in sections])
                ax2.set_xlim(0, 100)
                ax2.set_xlabel('Sentiment Score')
                ax2.set_title('Section Sentiments')
                ax2.axvline(x=50, color='gray', linestyle='--', alpha=0.5)
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=config.CHART_DPI, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Visualization generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Visualization error: {e}")
            return ""
    
    def _get_color(self, score: float) -> str:
        """Get color based on sentiment score."""
        if score >= 70:
            return '#28a745'  # Green
        elif score >= 55:
            return '#90ee90'  # Light green
        elif score >= 45:
            return '#ffc107'  # Yellow
        elif score >= 30:
            return '#ff9800'  # Orange
        else:
            return '#dc3545'  # Red


if __name__ == "__main__":
    # Test report generation
    test_result = {
        'success': True,
        'file_path': 'test_report.pdf',
        'analysis_date': datetime.now().isoformat(),
        'overall_sentiment': {
            'sentiment_score': 75.5,
            'sentiment_label': 'bullish',
            'confidence': 0.85,
            'method': 'finbert'
        },
        'extracted_metrics': {
            'price_target': 150.00,
            'rating': 'buy',
            'rating_score': 85
        },
        'risk_assessment': {
            'risk_level': 'medium',
            'risk_mentions': 5,
            'risk_adjustment': 1.0
        },
        'report_info': {
            'ticker': 'AAPL'
        }
    }
    
    generator = ReportGenerator()
    report_path = generator.generate_report(test_result, 'text')
    print(f"Test report generated: {report_path}")

# Made with Bob
