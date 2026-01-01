import logging
from datetime import datetime, timedelta
from jose import jwt
from app.infrastructure.config import settings

# Initialize logger for tracking token generation events
logger = logging.getLogger(__name__)

def create_access_token(user) -> str:
    """
    Generates a short-lived JWT Access Token.
    
    Payload:
    - sub: The User UUID (Standard subject claim)
    - email: Included for quick frontend display without a DB lookup
    - exp: Expiration timestamp (Default: 20 minutes)
    
    Dev Note: Access tokens should be short-lived to minimize damage if stolen.
    """
    expire = datetime.utcnow() + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    # Ensure user.id is a string as UUID objects aren't JSON serializable by default
    payload = {
        "sub": str(user.id), 
        "email": user.email, 
        "exp": expire
    }
    
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    logger.debug(f"JWT: Access token created for user {user.id}")
    return token

def create_refresh_token(user) -> str:
    """
    Generates a long-lived JWT Refresh Token.
    
    Purpose: Used to obtain a new access token without re-entering credentials.
    Logic Fix: Changed timedelta from 'minutes' to 'days' to match settings.
    """
    expire = datetime.utcnow() + timedelta(
        days=settings.refresh_token_expire_days
    )

    # We add a 'type' claim to prevent refresh tokens from being used as access tokens
    payload = {
        "sub": str(user.id), 
        "type": "refresh", 
        "exp": expire
    }

    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    logger.debug(f"JWT: Refresh token created for user {user.id}")
    return token