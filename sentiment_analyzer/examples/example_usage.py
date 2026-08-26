"""Example usage of the Sentiment Analyzer."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import (
    PDFRetriever,
    PDFExtractor,
    SentimentEngine,
    ReportGenerator,
    TradingIntegrator
)


def example_1_analyze_existing_pdf():
    """Example 1: Analyze an existing PDF report."""
    print("\n" + "="*60)
    print("Example 1: Analyze Existing PDF Report")
    print("="*60)
    
    # Path to your PDF report
    pdf_path = "data/sample_reports/AAPL_morningstar_report.pdf"
    
    # Create sentiment engine
    engine = SentimentEngine(model_name='finbert')
    
    # Analyze the report
    result = engine.analyze_report(pdf_path)
    
    if result['success']:
        print(f"\n✓ Analysis successful!")
        print(f"Sentiment Score: {result['overall_sentiment']['sentiment_score']:.2f}")
        print(f"Classification: {result['overall_sentiment']['sentiment_label'].upper()}")
        print(f"Confidence: {result['overall_sentiment']['confidence']:.2%}")
        
        # Generate report
        generator = ReportGenerator()
        report_path = generator.generate_report(result, 'text')
        print(f"\n✓ Report saved to: {report_path}")
    else:
        print(f"\n✗ Analysis failed: {result.get('error')}")


def example_2_download_and_analyze():
    """Example 2: Download report from Merrill and analyze."""
    print("\n" + "="*60)
    print("Example 2: Download and Analyze Report")
    print("="*60)
    
    ticker = 'MSFT'
    
    # Download report
    with PDFRetriever() as retriever:
        if retriever.authenticate():
            print(f"\n✓ Authenticated successfully")
            
            pdf_path = retriever.download_report(ticker)
            
            if pdf_path:
                print(f"✓ Report downloaded: {pdf_path}")
                
                # Analyze
                engine = SentimentEngine()
                result = engine.analyze_report(pdf_path)
                
                if result['success']:
                    print(f"\n✓ Sentiment Score: {result['overall_sentiment']['sentiment_score']:.2f}")
                    print(f"✓ Classification: {result['overall_sentiment']['sentiment_label'].upper()}")
            else:
                print(f"✗ Failed to download report for {ticker}")
        else:
            print("✗ Authentication failed")


def example_3_extract_and_analyze_sections():
    """Example 3: Extract specific sections and analyze separately."""
    print("\n" + "="*60)
    print("Example 3: Section-by-Section Analysis")
    print("="*60)
    
    pdf_path = "data/sample_reports/AAPL_morningstar_report.pdf"
    
    # Extract text
    extractor = PDFExtractor(pdf_path)
    extraction = extractor.extract()
    
    if extraction['success']:
        print(f"\n✓ Extracted {len(extraction['text'])} characters")
        
        # Extract sections
        sections = extractor.extract_sections()
        print(f"✓ Found {len(sections)} sections")
        
        # Analyze each section
        engine = SentimentEngine()
        
        for section_name, section_text in sections.items():
            if section_text:
                sentiment = engine.analyze_text(section_text)
                print(f"\n{section_name.replace('_', ' ').title()}:")
                print(f"  Score: {sentiment['sentiment_score']:.2f}")
                print(f"  Label: {sentiment['sentiment_label'].title()}")


def example_4_trading_integration():
    """Example 4: Generate trading signal with sentiment."""
    print("\n" + "="*60)
    print("Example 4: Trading Signal Generation")
    print("="*60)
    
    ticker = 'AAPL'
    technical_score = 72.5  # From your technical analysis
    current_price = 150.00
    
    # Create integrator
    integrator = TradingIntegrator()
    
    # Generate signal
    signal = integrator.generate_trading_signal(
        ticker=ticker,
        technical_score=technical_score,
        current_price=current_price
    )
    
    print(f"\n=== Trading Signal for {ticker} ===")
    print(f"Recommendation: {signal['recommendation']}")
    print(f"Combined Score: {signal['combined_score']:.2f}")
    print(f"  - Technical: {signal['technical_score']:.2f}")
    print(f"  - Sentiment: {signal['sentiment_score']:.2f}")
    print(f"\nPosition Multiplier: {signal['position_multiplier']:.2f}x")
    print(f"Sentiment: {signal['sentiment_label'].title()}")
    print(f"Risk Level: {signal['risk_level'].title()}")
    
    if signal.get('price_target'):
        print(f"\nPrice Target: ${signal['price_target']:.2f}")
        print(f"Upside Potential: {signal['upside_potential_pct']:.1f}%")
    
    print(f"\nRationale: {signal['rationale']}")


def example_5_batch_analysis():
    """Example 5: Batch analyze multiple stocks."""
    print("\n" + "="*60)
    print("Example 5: Batch Analysis")
    print("="*60)
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA']
    
    engine = SentimentEngine()
    results = {}
    
    for ticker in tickers:
        print(f"\nAnalyzing {ticker}...")
        
        # Find report (assumes reports are already downloaded)
        pdf_path = f"data/sample_reports/{ticker}_morningstar_report.pdf"
        
        if os.path.exists(pdf_path):
            result = engine.analyze_report(pdf_path)
            
            if result['success']:
                sentiment = result['overall_sentiment']
                results[ticker] = {
                    'score': sentiment['sentiment_score'],
                    'label': sentiment['sentiment_label'],
                    'confidence': sentiment['confidence']
                }
                print(f"  ✓ {sentiment['sentiment_label'].upper()} ({sentiment['sentiment_score']:.1f})")
            else:
                print(f"  ✗ Analysis failed")
        else:
            print(f"  ✗ Report not found")
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    for ticker, data in results.items():
        print(f"{ticker:6} | {data['label']:12} | Score: {data['score']:5.1f} | Confidence: {data['confidence']:.0%}")


def example_6_custom_configuration():
    """Example 6: Use custom configuration."""
    print("\n" + "="*60)
    print("Example 6: Custom Configuration")
    print("="*60)
    
    # Use VADER instead of FinBERT (faster, less accurate)
    engine = SentimentEngine(model_name='vader')
    
    pdf_path = "data/sample_reports/AAPL_morningstar_report.pdf"
    result = engine.analyze_report(pdf_path)
    
    if result['success']:
        print(f"\n✓ Analysis with VADER model")
        print(f"Sentiment Score: {result['overall_sentiment']['sentiment_score']:.2f}")
        print(f"Method: {result['overall_sentiment']['method'].upper()}")
        
        # Generate HTML report
        generator = ReportGenerator()
        report_path = generator.generate_report(result, 'html')
        print(f"\n✓ HTML report generated: {report_path}")
        
        # Generate visualization
        chart_path = generator.generate_visualization(result)
        if chart_path:
            print(f"✓ Chart generated: {chart_path}")


def example_7_sentiment_tracking():
    """Example 7: Track sentiment changes over time."""
    print("\n" + "="*60)
    print("Example 7: Sentiment Change Detection")
    print("="*60)
    
    ticker = 'AAPL'
    current_sentiment = 75.0  # Current analysis result
    
    integrator = TradingIntegrator()
    
    # Get historical sentiment
    history = integrator.get_sentiment_history(ticker, days=90)
    
    if history:
        print(f"\n✓ Found {len(history)} historical records")
        
        # Show trend
        print("\nSentiment History:")
        for record in history[-5:]:  # Last 5 records
            print(f"  {record['date'][:10]}: {record['sentiment_score']:.1f} ({record['sentiment_label']})")
        
        # Detect change
        alert = integrator.detect_sentiment_change(ticker, current_sentiment)
        
        if alert:
            print(f"\n⚠️  ALERT: Sentiment Change Detected!")
            print(f"Previous: {alert['previous_sentiment']:.1f}")
            print(f"Current: {alert['current_sentiment']:.1f}")
            print(f"Change: {alert['change']:+.1f} ({alert['direction']})")
        else:
            print("\n✓ No significant sentiment change")
    else:
        print("\n✗ No historical data available")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("SENTIMENT ANALYZER - USAGE EXAMPLES")
    print("="*60)
    
    examples = [
        ("Analyze Existing PDF", example_1_analyze_existing_pdf),
        ("Download and Analyze", example_2_download_and_analyze),
        ("Section Analysis", example_3_extract_and_analyze_sections),
        ("Trading Integration", example_4_trading_integration),
        ("Batch Analysis", example_5_batch_analysis),
        ("Custom Configuration", example_6_custom_configuration),
        ("Sentiment Tracking", example_7_sentiment_tracking),
    ]
    
    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nTo run a specific example, modify this script or call the function directly.")
    print("\nRunning Example 1 as demonstration...\n")
    
    # Run example 1 as demonstration
    try:
        example_1_analyze_existing_pdf()
    except Exception as e:
        print(f"\n✗ Example failed: {e}")
        print("Note: Make sure you have a PDF report in data/sample_reports/")


if __name__ == "__main__":
    main()

# Made with Bob
