"""Data fetcher agent for retrieving stock price data."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
from config import LOOKBACK_DAYS


class DataFetcherAgent:
    """Agent responsible for fetching and validating stock price data."""

    def __init__(self, lookback_days=LOOKBACK_DAYS):
        self.lookback_days = lookback_days
        self.data = None
        self.ticker = None
        self.company_name = None

    def fetch_stock_data(self, ticker, end_date=None, start_date=None):
        """
        Fetch historical stock data for a given ticker.

        Args:
            ticker (str): Stock ticker symbol (e.g., 'AAPL')
            end_date (str): End date in YYYY-MM-DD format (default: today)
            start_date (str): Start date in YYYY-MM-DD format (default: 1 year ago)

        Returns:
            dict: Data summary with status, message, and dataframe
        """
        try:
            if end_date is None:
                end_date = datetime.now()
            else:
                end_date = pd.to_datetime(end_date)

            if start_date is None:
                start_date = end_date - timedelta(days=self.lookback_days)
            else:
                start_date = pd.to_datetime(start_date)

            print(f"\n{'='*60}")
            print(f"Fetching stock data for {ticker.upper()}")
            print(f"Period: {start_date.date()} to {end_date.date()}")
            print(f"{'='*60}\n")

            # Fetch data using yfinance
            ticker_obj = yf.Ticker(ticker)
            data = ticker_obj.history(start=start_date, end=end_date)

            # Get company info
            try:
                self.company_name = ticker_obj.info.get('longName', ticker.upper())
            except:
                self.company_name = ticker.upper()

            if data.empty:
                return {
                    'status': 'error',
                    'message': f'No data found for ticker {ticker}. Please check the ticker symbol.',
                    'data': None
                }

            # Data validation
            data = self._validate_and_clean_data(data)

            self.data = data
            self.ticker = ticker.upper()

            # Summary statistics
            summary = self._generate_summary()

            return {
                'status': 'success',
                'message': f'Successfully fetched {len(data)} trading days for {self.company_name}',
                'data': data,
                'summary': summary
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error fetching data: {str(e)}',
                'data': None
            }

    def _validate_and_clean_data(self, data):
        """
        Validate and clean the fetched data.

        Args:
            data (pd.DataFrame): Raw data from yfinance

        Returns:
            pd.DataFrame: Cleaned data
        """
        # Reset index to make date a column
        data = data.reset_index()

        # Normalize column names to lowercase
        data.columns = data.columns.str.lower()
        data.rename(columns={'date': 'date'}, inplace=True)

        # Ensure required columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Required column '{col}' not found in data. Available: {list(data.columns)}")

        # Handle missing values
        if data.isnull().sum().sum() > 0:
            print("⚠️  Warning: Found missing values. Filling forward then backward...")
            data = data.fillna(method='ffill').fillna(method='bfill')

        # Ensure numeric types
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            data[col] = pd.to_numeric(data[col], errors='coerce')

        # Remove any rows with NaN after conversion
        data = data.dropna(subset=numeric_cols)

        # Sort by date
        data = data.sort_values('date').reset_index(drop=True)

        return data

    def _generate_summary(self):
        """Generate summary statistics for the data."""
        close_prices = self.data['close']

        return {
            'ticker': self.ticker,
            'company': self.company_name,
            'date_range': f"{self.data['date'].min().date()} to {self.data['date'].max().date()}",
            'total_records': len(self.data),
            'start_price': close_prices.iloc[0],
            'end_price': close_prices.iloc[-1],
            'min_price': close_prices.min(),
            'max_price': close_prices.max(),
            'avg_price': close_prices.mean(),
            'price_change_pct': ((close_prices.iloc[-1] - close_prices.iloc[0]) / close_prices.iloc[0]) * 100,
            'volatility': close_prices.pct_change().std() * 100,
            'avg_volume': self.data['volume'].mean(),
        }

    def get_summary(self):
        """Print formatted data summary."""
        if self.data is None:
            print("No data available. Please fetch data first.")
            return

        summary = self._generate_summary()

        print(f"\n{'='*60}")
        print(f"DATA SUMMARY FOR {summary['ticker']}")
        print(f"{'='*60}")
        print(f"Company:        {summary['company']}")
        print(f"Date Range:     {summary['date_range']}")
        print(f"Records:        {summary['total_records']}")
        print(f"\nPrice Statistics:")
        print(f"  Start Price:   ${summary['start_price']:.2f}")
        print(f"  End Price:     ${summary['end_price']:.2f}")
        print(f"  Min Price:     ${summary['min_price']:.2f}")
        print(f"  Max Price:     ${summary['max_price']:.2f}")
        print(f"  Avg Price:     ${summary['avg_price']:.2f}")
        print(f"  Change:        {summary['price_change_pct']:+.2f}%")
        print(f"  Volatility:    {summary['volatility']:.2f}%")
        print(f"  Avg Volume:    {summary['avg_volume']:,.0f}")
        print(f"{'='*60}\n")


def main():
    """Example usage of DataFetcherAgent."""
    agent = DataFetcherAgent()
    result = agent.fetch_stock_data('AAPL')

    if result['status'] == 'success':
        agent.get_summary()
        print("\nFirst few rows of data:")
        print(result['data'].head())
    else:
        print(f"Error: {result['message']}")


if __name__ == '__main__':
    main()
