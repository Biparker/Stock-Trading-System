"""Main entry point for Sentiment Analyzer CLI."""

import os
import sys
import argparse
import logging
from typing import List, Optional

from src import config
from src.pdf_retriever import PDFRetriever, setup_credentials_interactive
from src.pdf_extractor import PDFExtractor
from src.sentiment_engine import SentimentEngine
from src.report_generator import ReportGenerator
from src.trading_integrator import TradingIntegrator

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


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description='Stock Sentiment Analysis Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup credentials
  python main.py --setup-credentials
  
  # Analyze a specific PDF
  python main.py --ticker AAPL --pdf-path "reports/AAPL_report.pdf"
  
  # Download and analyze latest report
  python main.py --ticker MSFT --download-latest
  
  # Batch analysis
  python main.py --ticker-list AAPL MSFT GOOGL --download-latest
  
  # Generate trading signal
  python main.py --ticker AAPL --integrate-trading --technical-score 72.5 --current-price 150.00
        """
    )
    
    # Setup options
    parser.add_argument('--setup-credentials', action='store_true',
                       help='Setup Merrill Lynch credentials')
    
    # Analysis options
    parser.add_argument('--ticker', type=str,
                       help='Stock ticker symbol')
    parser.add_argument('--ticker-list', nargs='+',
                       help='List of stock ticker symbols')
    parser.add_argument('--pdf-path', type=str,
                       help='Path to PDF report')
    parser.add_argument('--download-latest', action='store_true',
                       help='Download latest report from Merrill')
    
    # Report options
    parser.add_argument('--report-format', choices=['text', 'json', 'html'],
                       default='text',
                       help='Report output format (default: text)')
    parser.add_argument('--output-path', type=str,
                       help='Custom output path for report')
    parser.add_argument('--generate-chart', action='store_true',
                       help='Generate sentiment visualization chart')
    
    # Trading integration options
    parser.add_argument('--integrate-trading', action='store_true',
                       help='Generate trading signal with sentiment')
    parser.add_argument('--technical-score', type=float,
                       help='Technical analysis score (0-100)')
    parser.add_argument('--current-price', type=float,
                       help='Current stock price')
    
    # Model options
    parser.add_argument('--model', choices=['finbert', 'vader', 'textblob'],
                       default=config.SENTIMENT_MODEL,
                       help=f'Sentiment analysis model (default: {config.SENTIMENT_MODEL})')
    
    # Utility options
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--version', action='version',
                       version=f'Sentiment Analyzer v{config.VERSION}')
    
    args = parser.parse_args()
    
    # Set verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle setup credentials
    if args.setup_credentials:
        setup_credentials_interactive()
        return
    
    # Validate required arguments
    if not args.ticker and not args.ticker_list:
        parser.error('Either --ticker or --ticker-list is required')
    
    # Process single ticker
    if args.ticker:
        process_ticker(args)
    
    # Process multiple tickers
    elif args.ticker_list:
        process_batch(args)


def process_ticker(args):
    """Process a single ticker."""
    ticker = args.ticker.upper()
    logger.info(f"Processing ticker: {ticker}")
    
    # Get PDF path
    pdf_path = args.pdf_path
    
    # Download if requested
    if args.download_latest:
        logger.info(f"Downloading latest report for {ticker}")
        with PDFRetriever() as retriever:
            if retriever.authenticate():
                pdf_path = retriever.download_report(ticker)
                if not pdf_path:
                    logger.error(f"Failed to download report for {ticker}")
                    return
            else:
                logger.error("Authentication failed")
                return
    
    # Check if PDF exists
    if not pdf_path:
        logger.error("No PDF path provided. Use --pdf-path or --download-latest")
        return
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return
    
    # Analyze sentiment
    logger.info("Analyzing sentiment...")
    engine = SentimentEngine(model_name=args.model)
    result = engine.analyze_report(pdf_path)
    
    if not result['success']:
        logger.error(f"Sentiment analysis failed: {result.get('error', 'Unknown error')}")
        return
    
    # Generate report
    logger.info(f"Generating {args.report_format} report...")
    generator = ReportGenerator()
    report_path = generator.generate_report(result, args.report_format, args.output_path)
    
    if report_path:
        print(f"\n[OK] Report generated: {report_path}")
    
    # Generate chart if requested
    if args.generate_chart:
        logger.info("Generating visualization...")
        chart_path = generator.generate_visualization(result)
        if chart_path:
            print(f"[OK] Chart generated: {chart_path}")
    
    # Trading integration
    if args.integrate_trading:
        if not args.technical_score or not args.current_price:
            logger.error("--technical-score and --current-price required for trading integration")
            return
        
        logger.info("Generating trading signal...")
        integrator = TradingIntegrator()
        signal = integrator.generate_trading_signal(
            ticker,
            args.technical_score,
            args.current_price,
            pdf_path
        )
        
        print(f"\n=== Trading Signal for {ticker} ===")
        print(f"Recommendation: {signal['recommendation']}")
        print(f"Combined Score: {signal['combined_score']:.2f}")
        print(f"Position Multiplier: {signal['position_multiplier']:.2f}x")
        print(f"\nRationale: {signal['rationale']}")
    
    # Print summary
    print(f"\n=== Sentiment Analysis Summary for {ticker} ===")
    print(f"Sentiment Score: {result['overall_sentiment']['sentiment_score']:.2f} / 100")
    print(f"Classification: {result['overall_sentiment']['sentiment_label'].upper()}")
    print(f"Confidence: {result['overall_sentiment']['confidence']:.2%}")
    print(f"Method: {result['overall_sentiment']['method'].upper()}")
    
    if result.get('extracted_metrics'):
        metrics = result['extracted_metrics']
        if 'price_target' in metrics:
            print(f"Price Target: ${metrics['price_target']:.2f}")
        if 'rating' in metrics:
            print(f"Analyst Rating: {metrics['rating'].title()}")


def process_batch(args):
    """Process multiple tickers."""
    tickers = [t.upper() for t in args.ticker_list]
    logger.info(f"Processing {len(tickers)} tickers: {', '.join(tickers)}")
    
    results = {}
    
    # Download reports if requested
    if args.download_latest:
        logger.info("Downloading reports...")
        with PDFRetriever() as retriever:
            if retriever.authenticate():
                download_results = retriever.download_batch(tickers)
                
                for ticker, pdf_path in download_results.items():
                    if pdf_path:
                        results[ticker] = {'pdf_path': pdf_path}
                    else:
                        logger.warning(f"Failed to download report for {ticker}")
            else:
                logger.error("Authentication failed")
                return
    
    # Analyze each ticker
    engine = SentimentEngine(model_name=args.model)
    generator = ReportGenerator()
    
    for ticker in tickers:
        logger.info(f"\nProcessing {ticker}...")
        
        # Get PDF path
        if ticker in results:
            pdf_path = results[ticker]['pdf_path']
        else:
            # Look for existing report
            pdf_path = None
            for filename in os.listdir(config.SAMPLE_REPORTS_DIR):
                if ticker in filename.upper() and filename.endswith('.pdf'):
                    pdf_path = os.path.join(config.SAMPLE_REPORTS_DIR, filename)
                    break
        
        if not pdf_path or not os.path.exists(pdf_path):
            logger.warning(f"No report found for {ticker}")
            continue
        
        # Analyze
        result = engine.analyze_report(pdf_path)
        
        if result['success']:
            # Generate report
            report_path = generator.generate_report(result, args.report_format)
            
            results[ticker] = {
                'pdf_path': pdf_path,
                'report_path': report_path,
                'sentiment_score': result['overall_sentiment']['sentiment_score'],
                'sentiment_label': result['overall_sentiment']['sentiment_label']
            }
            
            print(f"✓ {ticker}: {result['overall_sentiment']['sentiment_label'].upper()} "
                  f"({result['overall_sentiment']['sentiment_score']:.1f})")
        else:
            logger.error(f"Analysis failed for {ticker}")
    
    # Summary
    print(f"\n=== Batch Analysis Complete ===")
    print(f"Processed: {len(results)} / {len(tickers)} tickers")
    
    if results:
        print("\nSummary:")
        for ticker, data in results.items():
            print(f"  {ticker}: {data['sentiment_label'].upper()} ({data['sentiment_score']:.1f})")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

# Made with Bob
