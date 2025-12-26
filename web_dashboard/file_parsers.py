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
    """Extract text from a PDF file."""
    try:
        import pypdf
        reader = pypdf.PdfReader(file_obj)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except ImportError:
        logger.error("pypdf not installed. Please install it with `pip install pypdf`")
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
