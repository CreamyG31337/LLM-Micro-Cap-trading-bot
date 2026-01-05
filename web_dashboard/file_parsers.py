import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def extract_text_from_file(uploaded_file) -> Optional[str]:
    """
    Extract text content from an uploaded file (PDF or DOCX).
    
    Args:
        uploaded_file: Streamlit UploadedFile object or file-like object
        
    Returns:
        Extracted text string or None if extraction failed
    """
    try:
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        if file_type == 'pdf':
            return parse_pdf(uploaded_file)
        elif file_type == 'docx':
            return parse_docx(uploaded_file)
        else:
            logger.error(f"Unsupported file type: {file_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting text from file {uploaded_file.name}: {e}")
        return None

def parse_pdf(file_obj) -> Optional[str]:
    """Extract text from a PDF file using pdfplumber (better formatting than pypdf)."""
    try:
        import pdfplumber
        
        # Reset file pointer if it's a file-like object
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        
        text = ""
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text if text.strip() else None
    except ImportError:
        logger.error("pdfplumber not installed. Please install it with `pip install pdfplumber`")
        return None
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        return None

def parse_docx(file_obj) -> Optional[str]:
    """Extract text from a DOCX file."""
    try:
        import docx
        doc = docx.Document(file_obj)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except ImportError:
        logger.error("python-docx not installed. Please install it with `pip install python-docx`")
        return None
    except Exception as e:
        logger.error(f"Error parsing DOCX: {e}")
        return None
