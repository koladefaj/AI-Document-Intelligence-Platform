import logging
from typing import Annotated
from fastapi import Depends, HTTPException, APIRouter, Request, Body
from app.infrastructure.db.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette import status
from app.api.v1.schemas import RegisterRequest, LoginRequest,ResgisterResponse
from app.application.use_case.auth import change_password as change_password_uc
from app.application.use_case.auth import delete_user as delete_user_uc
from app.infrastructure.auth.dependencies import get_current_user
from app.infrastructure.db.session import get_session
from app.application.use_case.auth import register_user as register_uc, login as login_uc
from app.infrastructure.auth.jwt import create_access_token, create_refresh_token
from app.domain.exceptions import AuthenticationFailed
from app.core.limiter import limiter

# Initialize logger for security and audit events
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=ResgisterResponse)
@limiter.limit("5/hour")  # Strict limit to prevent bot-spamming account creation
async def register_user_route(
    request: Request,
    body: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)]
) -> ResgisterResponse:
    """
    User Registration Endpoint.
    
    Security: Limited to 5 attempts per hour to mitigate mass-account creation bots.
    """
    try:
        user = await register_uc(
            session=session, 
            email=body.email, 
            password=body.password,
            full_name=body.full_name
        )
        
        logger.info(f"Auth: New user created with ID {user.id}")
        
        # Auto-generate tokens for instant login
        access_token = create_access_token(user)
        refresh_token = create_refresh_token(user)

        return ResgisterResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            access_token=access_token,
            refresh_token=refresh_token,
            message="Account created successfully"
        )
        
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
    session: Annotated[AsyncSession, Depends(get_session)]
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
        # log the specific email but return a generic 401 to prevent account enumeration
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
    
@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password_route(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],  # fetched from JWT
    old_password: str = Body(...),
    new_password: str = Body(...),
):
    """
    Allows the currently logged-in user to update their password.
    Security:
        - Must provide the old password
        - Logs the change for audit
    """
    try:
        await change_password_uc(
            session=session,
            user_id=current_user.id,
            old_password=old_password,
            new_password=new_password
        )
        logger.info(f"Auth: Password changed for user {current_user.email}")
        return {"message": "Password updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth Critical: Change password failed for {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not change password."
        )


@router.delete("/delete-account", status_code=status.HTTP_200_OK)
async def delete_account_route(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Deletes or deactivates the current user's account.
    Security:
        - Must be authenticated
        - Soft delete for audit/logging purposes
    """
    try:
        await delete_user_uc(session=session, user_id=current_user.id)
        logger.info(f"Auth: Account deleted for user {current_user.email}")
        return {"message": "Account successfully deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth Critical: Delete account failed for {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete account."
        )

@router.get("/me", response_model=ResgisterResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get the currently authenticated user's profile.
    """
    return ResgisterResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        message="Profile retrieved successfully"
    )

@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token_route(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    refresh_token: str = Body(..., embed=True)
):
    """
    Refresh Token Endpoint.
    """
    from jose import jwt, JWTError
    from app.infrastructure.config import settings
    from app.infrastructure.auth.jwt import create_access_token
    import uuid

    try:
        payload = jwt.decode(
            refresh_token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        user_id_str = payload.get("sub")
        user_uuid = uuid.UUID(user_id_str)
        result = await session.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        return {
            "access_token": create_access_token(user),
            "token_type": "bearer"
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid")

