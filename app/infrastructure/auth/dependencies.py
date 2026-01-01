import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from sqlalchemy import select

from app.infrastructure.config import settings
from app.infrastructure.db.session import get_session
from app.infrastructure.db.models import User

# Initialize logger for security events
logger = logging.getLogger(__name__)

# HTTPBearer is used for "Authorization: Bearer <token>" headers
oauth2_scheme = HTTPBearer()

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Dependency that authenticates requests using a JWT.
    
    Workflow:
    1. Extracts credentials from the Bearer token.
    2. Decodes and validates the JWT using the SECRET_KEY.
    3. Lookups the user in the database to ensure they still exist and are active.
    
    Dev Note: In Docker production, ensure SECRET_KEY is never the default 'secret'.
    """
    try:
        # Decode the token
        payload = jwt.decode(
            token.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # 'sub' (subject) is the standard JWT claim for the user identifier
        user_id: str = payload.get("sub")

        if not user_id:
            logger.warning("Auth Failure: Token missing 'sub' claim.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid authentication token"
            )

    except JWTError as e:
        logger.error(f"JWT Decode Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token is invalid or has expired"
        )

    # --- DATABASE VERIFICATION ---
    # Dev Note: We query the DB for every authenticated request to ensure
    # we can handle 'banned' or 'deleted' users instantly.
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Auth Failure: User {user_id} not found in database.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User not found"
        )
    
    if not user.is_active:
        logger.warning(f"Auth Failure: User {user_id} is inactive.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="User account is disabled"
        )

    return user