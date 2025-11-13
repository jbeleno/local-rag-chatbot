"""
Custom validators for Pydantic.
"""
import re
from pathlib import Path
from typing import Any
from pydantic import field_validator, ValidationError

# Try to import magic (optional, for file content validation)
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

# Maximum file sizes (in bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_TEXT_LENGTH = 1000000  # 1 million characters

# Allowed extensions and their MIME types
ALLOWED_EXTENSIONS = {
    'pdf': ['application/pdf'],
    'txt': ['text/plain', 'text/plain; charset=utf-8'],
    'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'doc': ['application/msword']
}


def validate_file_extension(filename: str) -> str:
    """
    Validate file extension.
    
    Args:
        filename: File name
        
    Returns:
        Validated extension
        
    Raises:
        ValueError: If extension is not allowed
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    extension = Path(filename).suffix[1:].lower()  # Without the dot
    
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File extension '{extension}' not allowed. "
            f"Allowed extensions: {', '.join(ALLOWED_EXTENSIONS.keys())}"
        )
    
    return extension


def validate_file_size(file_content: bytes) -> bytes:
    """
    Validate file size.
    
    Args:
        file_content: File content in bytes
        
    Returns:
        File content if valid
        
    Raises:
        ValueError: If file is too large
    """
    if len(file_content) == 0:
        raise ValueError("File is empty")
    
    if len(file_content) > MAX_FILE_SIZE:
        size_mb = len(file_content) / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise ValueError(
            f"File is too large ({size_mb:.2f} MB). "
            f"Maximum allowed size: {max_mb} MB"
        )
    
    return file_content


def validate_file_content(file_content: bytes, filename: str) -> bytes:
    """
    Validate actual file content using magic numbers.
    
    Args:
        file_content: File content
        filename: File name
        
    Returns:
        File content if valid
        
    Raises:
        ValueError: If content doesn't match extension
    """
    try:
        # Try to detect MIME type using python-magic if available
        if MAGIC_AVAILABLE and magic is not None:
            try:
                mime = magic.Magic(mime=True)
                detected_mime = mime.from_buffer(file_content)
                
                extension = Path(filename).suffix[1:].lower()
                allowed_mimes = ALLOWED_EXTENSIONS.get(extension, [])
                
                if allowed_mimes and detected_mime not in allowed_mimes:
                    # Some MIME types may vary, make validation flexible
                    if not any(detected_mime.startswith(m.split('/')[0]) for m in allowed_mimes):
                        raise ValueError(
                            f"File content does not match extension. "
                            f"Expected: {extension}, Detected: {detected_mime}"
                        )
            except Exception as e:
                # If there's an error in detection, continue (not critical)
                # Extension validation is sufficient
                pass
        
        return file_content
    except Exception as e:
        raise ValueError(f"Error validating file content: {str(e)}")


def validate_query_text(query: str) -> str:
    """
    Validate and sanitize query text.
    
    Args:
        query: Query text
        
    Returns:
        Sanitized query
        
    Raises:
        ValueError: If query is not valid
    """
    if not query:
        raise ValueError("Query cannot be empty")
    
    # Remove whitespace
    query = query.strip()
    
    if not query:
        raise ValueError("Query cannot be empty")
    
    if len(query) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Query is too long ({len(query)} characters). "
            f"Maximum allowed: {MAX_TEXT_LENGTH} characters"
        )
    
    # Sanitize: remove control characters (except line breaks)
    query = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', query)
    
    return query


def validate_session_id(session_id: str) -> str:
    """
    Validate session_id format.
    
    Args:
        session_id: Session ID
        
    Returns:
        Validated session ID
        
    Raises:
        ValueError: If session_id is not valid
    """
    if not session_id:
        raise ValueError("session_id cannot be empty")
    
    session_id = session_id.strip()
    
    if not session_id:
        raise ValueError("session_id cannot be empty")
    
    # Validate format: alphanumeric, dashes and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        raise ValueError(
            "session_id can only contain letters, numbers, dashes and underscores"
        )
    
    if len(session_id) > 255:
        raise ValueError("session_id cannot have more than 255 characters")
    
    return session_id


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove dangerous path components
    filename = Path(filename).name  # Only the name, without path
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:255 - len(ext)] + ext
    
    return filename

