import logging
from fastapi import Depends, HTTPException, APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.v1.schemas import RegisterRequest, LoginRequest
from app.infrastructure.db.session import get_session
from app.application.use_case.auth import register_user as register_uc, login as login_uc
from app.domain.exceptions import AuthenticationFailed
from app.core.limiter import limiter

# Initialize logger for security and audit events
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")  # Strict limit to prevent bot-spamming account creation
async def register_user_route(
    request: Request,
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    User Registration Endpoint.
    
    Security: Limited to 5 attempts per hour to mitigate mass-account creation bots.
    """
    try:
        user = await register_uc(session=session, email=body.email, password=body.password)
        
        logger.info(f"Auth: New user created with ID {user.id}")
        
        return {
            "id": str(user.id), 
            "email": user.email, 
            "role": user.role,
            "message": "Account created successfully"
        }
        
    except AuthenticationFailed as e:
        # Handles 'User already exists' gracefully
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Auth Critical: Registration error for {body.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Could not complete registration."
        )

@router.post("/login", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute") # Standard limit for human login attempts
async def login_user_route(
    request: Request,
    body: LoginRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Login Endpoint.
    
    Returns:
        Access and Refresh tokens upon successful verification.
    """
    try:
        tokens = await login_uc(email=body.email, password=body.password, session=session)
        
        logger.info(f"Auth: Login successful for user {body.email}")
        return tokens

    except AuthenticationFailed:
        # We log the specific email but return a generic 401 to prevent account enumeration
        logger.warning(f"Auth: Failed login attempt for {body.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password"
        )
    except Exception as e:
        logger.error(f"Auth Critical: Login error for {body.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred during login."
        )