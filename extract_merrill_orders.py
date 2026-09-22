import PyPDF2
import sys

def extract_pdf_text(pdf_path):
    """Extract text from PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            return text
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"

if __name__ == "__main__":
    pdf_path = "Orders/Merrill_Orders_060926.pdf"
    text = extract_pdf_text(pdf_path)
    print(text)
    
    # Save to file for review
    with open("Orders/extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("\n\nText saved to Orders/extracted_text.txt")

# Made with Bob
