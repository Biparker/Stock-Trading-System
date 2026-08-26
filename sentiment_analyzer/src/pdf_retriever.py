"""PDF Retrieval Agent for downloading Morningstar reports from Merrill Lynch."""

import os
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from cryptography.fernet import Fernet

from . import config

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


class PDFRetriever:
    """Agent for retrieving PDF reports from Merrill Lynch account."""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize PDF Retriever.
        
        Args:
            username: Merrill Lynch username (optional if using stored credentials)
            password: Merrill Lynch password (optional if using stored credentials)
        """
        self.username = username
        self.password = password
        self.session = None
        self.driver = None
        self.authenticated = False
        
        # Load credentials if not provided
        if not self.username or not self.password:
            self._load_credentials()
        
        logger.info("PDFRetriever initialized")
    
    def _load_credentials(self):
        """Load encrypted credentials from file."""
        try:
            if os.path.exists(config.CREDENTIALS_FILE) and os.path.exists(config.ENCRYPTION_KEY_FILE):
                with open(config.ENCRYPTION_KEY_FILE, 'rb') as key_file:
                    key = key_file.read()
                
                cipher = Fernet(key)
                
                with open(config.CREDENTIALS_FILE, 'rb') as cred_file:
                    encrypted_data = cred_file.read()
                
                decrypted_data = cipher.decrypt(encrypted_data).decode()
                username, password = decrypted_data.split(':', 1)
                
                self.username = username
                self.password = password
                logger.info("Credentials loaded successfully")
            else:
                logger.warning("No stored credentials found")
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
    
    def save_credentials(self, username: str, password: str):
        """
        Save encrypted credentials to file.
        
        Args:
            username: Merrill Lynch username
            password: Merrill Lynch password
        """
        try:
            # Generate encryption key if it doesn't exist
            if not os.path.exists(config.ENCRYPTION_KEY_FILE):
                key = Fernet.generate_key()
                with open(config.ENCRYPTION_KEY_FILE, 'wb') as key_file:
                    key_file.write(key)
            else:
                with open(config.ENCRYPTION_KEY_FILE, 'rb') as key_file:
                    key = key_file.read()
            
            cipher = Fernet(key)
            
            # Encrypt credentials
            credentials = f"{username}:{password}"
            encrypted_data = cipher.encrypt(credentials.encode())
            
            # Save encrypted credentials
            with open(config.CREDENTIALS_FILE, 'wb') as cred_file:
                cred_file.write(encrypted_data)
            
            self.username = username
            self.password = password
            logger.info("Credentials saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            raise
    
    def _setup_session(self):
        """Setup requests session with retry logic."""
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=config.MERRILL_MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _setup_driver(self):
        """Setup Selenium WebDriver for browser automation."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in background
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # Set download directory
        prefs = {
            'download.default_directory': config.SAMPLE_REPORTS_DIR,
            'download.prompt_for_download': False,
            'plugins.always_open_pdf_externally': True
        }
        options.add_experimental_option('prefs', prefs)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing WebDriver: {e}")
            raise
    
    def authenticate(self) -> bool:
        """
        Authenticate with Merrill Lynch.
        
        Returns:
            bool: True if authentication successful
        """
        if not self.username or not self.password:
            logger.error("Username and password required for authentication")
            return False
        
        try:
            self._setup_driver()
            
            logger.info("Navigating to Merrill Lynch login page")
            self.driver.get(config.MERRILL_LOGIN_URL)
            
            # Wait for login form
            wait = WebDriverWait(self.driver, config.MERRILL_TIMEOUT)
            
            # Enter username
            username_field = wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_field.send_keys(self.username)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.password)
            
            # Click login button
            login_button = self.driver.find_element(By.ID, "login-button")
            login_button.click()
            
            # Wait for successful login (adjust selector based on actual page)
            wait.until(EC.url_contains("account"))
            
            self.authenticated = True
            logger.info("Authentication successful")
            return True
            
        except TimeoutException:
            logger.error("Login timeout - check credentials or page structure")
            return False
        except NoSuchElementException as e:
            logger.error(f"Login element not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def download_report(
        self,
        ticker: str,
        report_type: str = config.DEFAULT_REPORT_TYPE,
        save_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Download analyst report for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            report_type: Type of report to download
            save_path: Custom save path (optional)
        
        Returns:
            str: Path to downloaded PDF file, or None if failed
        """
        if not self.authenticated:
            logger.info("Not authenticated, attempting authentication")
            if not self.authenticate():
                logger.error("Authentication failed, cannot download report")
                return None
        
        try:
            logger.info(f"Downloading {report_type} report for {ticker}")
            
            # Navigate to research section
            research_url = f"{config.MERRILL_RESEARCH_URL}?symbol={ticker}"
            self.driver.get(research_url)
            
            wait = WebDriverWait(self.driver, config.MERRILL_TIMEOUT)
            
            # Find Morningstar report link (adjust selector based on actual page)
            report_link = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//a[contains(text(), 'Morningstar') or contains(@href, 'morningstar')]")
                )
            )
            
            # Click to download
            report_link.click()
            
            # Wait for download to complete
            time.sleep(5)  # Adjust based on file size
            
            # Find downloaded file
            if save_path is None:
                save_path = os.path.join(
                    config.SAMPLE_REPORTS_DIR,
                    f"{ticker}_{report_type}_{datetime.now().strftime('%Y%m%d')}.pdf"
                )
            
            # Check if file was downloaded
            downloaded_files = [
                f for f in os.listdir(config.SAMPLE_REPORTS_DIR)
                if f.endswith('.pdf') and ticker.upper() in f.upper()
            ]
            
            if downloaded_files:
                # Get most recent file
                latest_file = max(
                    [os.path.join(config.SAMPLE_REPORTS_DIR, f) for f in downloaded_files],
                    key=os.path.getctime
                )
                
                # Rename to standard format
                os.rename(latest_file, save_path)
                
                logger.info(f"Report downloaded successfully: {save_path}")
                return save_path
            else:
                logger.error("Download failed - file not found")
                return None
                
        except TimeoutException:
            logger.error(f"Timeout downloading report for {ticker}")
            return None
        except Exception as e:
            logger.error(f"Error downloading report: {e}")
            return None
    
    def download_batch(
        self,
        tickers: List[str],
        report_type: str = config.DEFAULT_REPORT_TYPE
    ) -> Dict[str, Optional[str]]:
        """
        Download reports for multiple tickers.
        
        Args:
            tickers: List of stock ticker symbols
            report_type: Type of report to download
        
        Returns:
            dict: Mapping of ticker to downloaded file path
        """
        results = {}
        
        for i, ticker in enumerate(tickers):
            logger.info(f"Processing {i+1}/{len(tickers)}: {ticker}")
            
            try:
                file_path = self.download_report(ticker, report_type)
                results[ticker] = file_path
                
                # Rate limiting
                if i < len(tickers) - 1:
                    time.sleep(config.BATCH_DELAY_SECONDS)
                    
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                results[ticker] = None
                
                if not config.CONTINUE_ON_ERROR:
                    break
        
        logger.info(f"Batch download complete: {len([v for v in results.values() if v])} successful")
        return results
    
    def check_report_availability(self, ticker: str) -> bool:
        """
        Check if Morningstar report is available for ticker.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            bool: True if report available
        """
        if not self.authenticated:
            if not self.authenticate():
                return False
        
        try:
            research_url = f"{config.MERRILL_RESEARCH_URL}?symbol={ticker}"
            self.driver.get(research_url)
            
            wait = WebDriverWait(self.driver, 10)
            
            # Check for Morningstar link
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//a[contains(text(), 'Morningstar')]")
                    )
                )
                logger.info(f"Morningstar report available for {ticker}")
                return True
            except TimeoutException:
                logger.info(f"No Morningstar report found for {ticker}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False
    
    def close(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")
        
        if self.session:
            self.session.close()
            logger.info("Session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def setup_credentials_interactive():
    """Interactive setup for credentials."""
    print("\n=== Merrill Lynch Credentials Setup ===")
    print("Your credentials will be encrypted and stored securely.")
    print("They will never be transmitted or shared.\n")
    
    username = input("Enter Merrill Lynch username: ").strip()
    password = input("Enter Merrill Lynch password: ").strip()
    
    if not username or not password:
        print("Error: Username and password cannot be empty")
        return False
    
    try:
        retriever = PDFRetriever()
        retriever.save_credentials(username, password)
        print("\n✓ Credentials saved successfully!")
        return True
    except Exception as e:
        print(f"\n✗ Error saving credentials: {e}")
        return False


if __name__ == "__main__":
    # Test the retriever
    setup_credentials_interactive()

# Made with Bob
