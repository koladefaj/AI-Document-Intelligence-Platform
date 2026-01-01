import magic
import logging
from fastapi import HTTPException, status, UploadFile

# Initialize logger for security events
logger = logging.getLogger(__name__)

# --- 1. CONFIGURATION ---
# Dev Note: We explicitly map MIME types to allowed extensions.
# This prevents 'Polyglot' files (files that are valid in two different formats).
ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/msword": [".doc"],
    "text/plain": [".txt"],
    "application/zip": [".docx", ".zip"]  # Word files are technically ZIP structures
}

# Max file size: 10MB (Standard for document processing tasks)
MAX_FILE_SIZE = 10 * 1024 * 1024 

async def validate_file_content(file: UploadFile):
    """
    Performs multi-stage validation on uploaded files.
    
    1. Size Check: Prevents RAM exhaustion (DoS attacks).
    2. Magic Byte Check: Identifies real file type via binary headers.
    3. Extension Check: Ensures filename extension matches binary content.
    """
    
    # --- STAGE 1: SIZE VALIDATION ---
    file_size = 0
    if file.size:
        file_size = file.size
    else:
        # Fallback for clients with missing headers
        await file.seek(0, 2)
        file_size = await file.tell()
        await file.seek(0)

    if file_size > MAX_FILE_SIZE:
        logger.warning(f"Security: Blocked oversized file ({file_size} bytes)")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds 10MB limit."
        )

    # --- STAGE 2: CONTENT VALIDATION (Magic Bytes) ---
    # We only read the first 2KB. This is enough to identify 99% of file types
    # without loading the entire file into memory.
    header = await file.read(2048)
    file_mime_type = magic.from_buffer(header, mime=True)
    await file.seek(0) # Critical: Reset cursor so the next service can read from the start

    if file_mime_type not in ALLOWED_MIME_TYPES:
        logger.error(f"Security: Rejected unsupported MIME type: {file_mime_type}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file_mime_type}"
        )

    # --- STAGE 3: EXTENSION CONSISTENCY ---
    # Prevents 'Masquerading' (e.g., a file named 'virus.pdf' that is actually a .sh script)
    file_ext = "." + file.filename.split(".")[-1].lower() if file.filename else ""
    if file_ext not in ALLOWED_MIME_TYPES[file_mime_type]:
        logger.error(f"Security: Extension mismatch. {file_ext} vs {file_mime_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File extension does not match the actual file content."
        )

    # Final cursor reset for the Storage/Upload service
    await file.seek(0)
    return True