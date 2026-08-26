"""PDF Text Extraction Agent for processing analyst reports."""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pdfplumber
import PyPDF2
from pdfminer.high_level import extract_text as pdfminer_extract

from . import config

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Agent for extracting text and data from PDF analyst reports."""
    
    def __init__(self, pdf_path: str):
        """
        Initialize PDF Extractor.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        self.text = ""
        self.tables = []
        self.metadata = {}
        self.extracted = False
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"PDFExtractor initialized for: {pdf_path}")
    
    def extract(self, method: str = config.PDF_EXTRACTION_METHOD) -> Dict:
        """
        Extract text from PDF using specified method.
        
        Args:
            method: Extraction method ('pdfplumber', 'pypdf2', 'pdfminer')
        
        Returns:
            dict: Extracted content including text, tables, and metadata
        """
        logger.info(f"Extracting PDF using method: {method}")
        
        try:
            if method == 'pdfplumber':
                self._extract_with_pdfplumber()
            elif method == 'pypdf2':
                self._extract_with_pypdf2()
            elif method == 'pdfminer':
                self._extract_with_pdfminer()
            else:
                logger.warning(f"Unknown method {method}, using pdfplumber")
                self._extract_with_pdfplumber()
            
            # Validate extraction
            if len(self.text) < config.MIN_TEXT_LENGTH:
                logger.warning(f"Extracted text too short ({len(self.text)} chars)")
                # Try alternative method
                if method != 'pdfminer':
                    logger.info("Trying pdfminer as fallback")
                    self._extract_with_pdfminer()
            
            self.extracted = True
            logger.info(f"Extraction complete: {len(self.text)} characters")
            
            return {
                'text': self.text,
                'tables': self.tables,
                'metadata': self.metadata,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {
                'text': '',
                'tables': [],
                'metadata': {},
                'success': False,
                'error': str(e)
            }
    
    def _extract_with_pdfplumber(self):
        """Extract text using pdfplumber (best for tables)."""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Extract metadata
                self.metadata = {
                    'pages': len(pdf.pages),
                    'creator': pdf.metadata.get('Creator', ''),
                    'producer': pdf.metadata.get('Producer', ''),
                    'creation_date': pdf.metadata.get('CreationDate', '')
                }
                
                # Extract text from all pages
                text_parts = []
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    
                    # Extract tables if enabled
                    if config.EXTRACT_TABLES:
                        tables = page.extract_tables()
                        if tables:
                            for table in tables:
                                self.tables.append({
                                    'page': page_num,
                                    'data': table
                                })
                
                self.text = '\n\n'.join(text_parts)
                logger.info(f"pdfplumber: Extracted {len(self.text)} chars, {len(self.tables)} tables")
                
        except Exception as e:
            logger.error(f"pdfplumber extraction error: {e}")
            raise
    
    def _extract_with_pypdf2(self):
        """Extract text using PyPDF2 (fast, basic extraction)."""
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                info = reader.metadata
                self.metadata = {
                    'pages': len(reader.pages),
                    'creator': info.get('/Creator', '') if info else '',
                    'producer': info.get('/Producer', '') if info else '',
                    'title': info.get('/Title', '') if info else ''
                }
                
                # Extract text from all pages
                text_parts = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                self.text = '\n\n'.join(text_parts)
                logger.info(f"PyPDF2: Extracted {len(self.text)} chars")
                
        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {e}")
            raise
    
    def _extract_with_pdfminer(self):
        """Extract text using pdfminer (robust, handles complex layouts)."""
        try:
            self.text = pdfminer_extract(self.pdf_path)
            
            # Get basic metadata
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                self.metadata = {
                    'pages': len(reader.pages)
                }
            
            logger.info(f"pdfminer: Extracted {len(self.text)} chars")
            
        except Exception as e:
            logger.error(f"pdfminer extraction error: {e}")
            raise
    
    def clean_text(self) -> str:
        """
        Clean and normalize extracted text.
        
        Returns:
            str: Cleaned text
        """
        if not self.text:
            return ""
        
        text = self.text
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers (common patterns)
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\s*\|\s*Page', '', text)
        
        # Remove headers/footers (common patterns)
        text = re.sub(r'Morningstar\s+Equity\s+Research', '', text, flags=re.IGNORECASE)
        text = re.sub(r'©\s*\d{4}\s+Morningstar', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        logger.info(f"Text cleaned: {len(text)} chars")
        return text
    
    def extract_sections(self) -> Dict[str, str]:
        """
        Extract common report sections.
        
        Returns:
            dict: Sections with their content
        """
        if not self.text:
            return {}
        
        sections = {}
        text = self.clean_text()
        
        # Common section headers in Morningstar reports
        section_patterns = {
            'executive_summary': r'(?:Executive\s+Summary|Summary)(.*?)(?=\n[A-Z][a-z]+\s+[A-Z]|$)',
            'investment_thesis': r'(?:Investment\s+Thesis|Thesis)(.*?)(?=\n[A-Z][a-z]+\s+[A-Z]|$)',
            'valuation': r'(?:Valuation|Fair\s+Value)(.*?)(?=\n[A-Z][a-z]+\s+[A-Z]|$)',
            'risks': r'(?:Risk|Risks|Risk\s+Factors)(.*?)(?=\n[A-Z][a-z]+\s+[A-Z]|$)',
            'financial_outlook': r'(?:Financial\s+Outlook|Outlook)(.*?)(?=\n[A-Z][a-z]+\s+[A-Z]|$)',
            'recommendation': r'(?:Recommendation|Rating)(.*?)(?=\n[A-Z][a-z]+\s+[A-Z]|$)'
        }
        
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                sections[section_name] = match.group(1).strip()
                logger.debug(f"Found section: {section_name}")
        
        logger.info(f"Extracted {len(sections)} sections")
        return sections
    
    def extract_key_phrases(self, max_phrases: int = 20) -> List[str]:
        """
        Extract key phrases from text.
        
        Args:
            max_phrases: Maximum number of phrases to extract
        
        Returns:
            list: Key phrases
        """
        if not self.text:
            return []
        
        text = self.clean_text()
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        # Filter sentences by length and content
        key_phrases = []
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Check if sentence contains important keywords
            if any(keyword in sentence.lower() for keyword in 
                   config.POSITIVE_KEYWORDS + config.NEGATIVE_KEYWORDS + config.RISK_KEYWORDS):
                if config.MIN_SENTENCE_LENGTH <= len(sentence) <= config.MAX_SENTENCE_LENGTH:
                    key_phrases.append(sentence)
        
        # Return top phrases
        return key_phrases[:max_phrases]
    
    def get_report_info(self) -> Dict:
        """
        Extract report metadata and basic information.
        
        Returns:
            dict: Report information
        """
        info = {
            'file_path': self.pdf_path,
            'file_name': os.path.basename(self.pdf_path),
            'file_size': os.path.getsize(self.pdf_path),
            'extraction_date': datetime.now().isoformat(),
            'text_length': len(self.text),
            'num_tables': len(self.tables),
            'metadata': self.metadata
        }
        
        # Try to extract ticker from filename
        # Match the last uppercase-starting word segment before the extension,
        # skipping known prefixes like "Analyst"
        filename = os.path.basename(self.pdf_path)
        name_stem = os.path.splitext(filename)[0]  # e.g. "Analyst_Meta"
        parts = re.split(r'[_\s\-]+', name_stem)
        skip_prefixes = {'analyst', 'report', 'equity', 'research'}
        ticker = None
        for part in parts:
            if part.lower() not in skip_prefixes and re.match(r'^[A-Za-z]{1,5}$', part):
                ticker = part.upper()
        if ticker:
            info['ticker'] = ticker
        
        # Try to extract date from filename
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            try:
                date_str = date_match.group(1)
                info['report_date'] = datetime.strptime(date_str, '%Y%m%d').isoformat()
            except:
                pass
        
        return info
    
    def save_extracted_text(self, output_path: Optional[str] = None) -> str:
        """
        Save extracted text to file.
        
        Args:
            output_path: Custom output path (optional)
        
        Returns:
            str: Path to saved file
        """
        if not self.text:
            logger.warning("No text to save")
            return ""
        
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            output_path = os.path.join(
                config.OUTPUT_DIR,
                f"{base_name}_extracted.txt"
            )
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(self.clean_text())
            
            logger.info(f"Extracted text saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error saving extracted text: {e}")
            return ""


def extract_from_multiple_pdfs(pdf_paths: List[str]) -> Dict[str, Dict]:
    """
    Extract text from multiple PDF files.
    
    Args:
        pdf_paths: List of PDF file paths
    
    Returns:
        dict: Mapping of file path to extraction results
    """
    results = {}
    
    for pdf_path in pdf_paths:
        logger.info(f"Processing: {pdf_path}")
        
        try:
            extractor = PDFExtractor(pdf_path)
            result = extractor.extract()
            results[pdf_path] = result
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            results[pdf_path] = {
                'success': False,
                'error': str(e)
            }
    
    return results


if __name__ == "__main__":
    # Test the extractor
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        extractor = PDFExtractor(pdf_path)
        result = extractor.extract()
        
        print(f"\n=== Extraction Results ===")
        print(f"Success: {result['success']}")
        print(f"Text length: {len(result['text'])} characters")
        print(f"Tables found: {len(result['tables'])}")
        print(f"\nFirst 500 characters:")
        print(result['text'][:500])
    else:
        print("Usage: python pdf_extractor.py <path_to_pdf>")

# Made with Bob
