import logging
import bcrypt

# Initialize logger
logger = logging.getLogger(__name__)

# Bcrypt has a maximum input length of 72 bytes. 
MAX_BYTE_LENGTH = 72

def hash_password(password: str) -> str:
    """Hashes a plain-text password using native Bcrypt."""
    # Ensure UTF-8 byte length check (some emojis/chars are > 1 byte)
    if len(password.encode("utf-8")) > MAX_BYTE_LENGTH:
        logger.warning("Password hashing failed: Input exceeds 72-byte limit.")
        raise ValueError("Password is too long (max 72 bytes).")

    # hashpw returns bytes, so we decode to utf-8 string for DB storage
    return bcrypt.hashpw(
        password.encode("utf-8"), 
        bcrypt.gensalt()
    ).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a stored hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), 
            hashed_password.encode("utf-8")
        )
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False