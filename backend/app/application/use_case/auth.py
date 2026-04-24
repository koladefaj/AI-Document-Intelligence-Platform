import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.db.models import User
from app.infrastructure.auth.password import hash_password, verify_password
from app.infrastructure.auth.jwt import create_refresh_token, create_access_token
from app.domain.exceptions import AuthenticationFailed

# Initialize logger for tracking auth events
logger = logging.getLogger(__name__)

async def register_user(session: AsyncSession, email: str, password: str, full_name: str | None = None) -> User:
    """
    Handles new user creation.
    """
    # Check for existing user
    result = await session.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        logger.warning(f"Registration failed: User {email} already exists.")
        raise AuthenticationFailed("A user with this email is already registered.")

    # Create and save user
    new_user = User(
        email=email, 
        full_name=full_name,
        hashed_password=hash_password(password)
    )
    
    session.add(new_user)
    await session.commit()
    # Refresh to get the generated UUID back from the DB
    await session.refresh(new_user)
    
    logger.info(f"User registered successfully: {new_user.id}")
    return new_user

async def login(
    session: AsyncSession,
    email: str,
    password: str,
) -> dict:
    """
    Validates user credentials and issues tokens.
    
    Returns:
        dict: Containing 'access_token' and 'refresh_token'
    """
    # 1. Fetch user by email
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # 2. Verify identity and status
    if not user or not verify_password(password, user.hashed_password):
        logger.warning(f"Login failed: Invalid credentials for {email}")
        raise AuthenticationFailed("Invalid email or password.")
    
    if not user.is_active:
        logger.warning(f"Login blocked: Account disabled for {email}")
        raise AuthenticationFailed("User account is inactive. Please contact support.")

    # 3. Generate tokens
    logger.info(f"Login successful: User {user.id}")
    return {
        "access_token": create_access_token(user),
        "refresh_token": create_refresh_token(user),
        "token_type": "bearer"
    }

async def delete_user(session: AsyncSession, user_id: str) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AuthenticationFailed("User not found.")
    
    # Soft delete
    dummy_password = hash_password("deleted_user_dummy_password")

    user.is_active = False
    user.email = f"deleted_{user.id}@example.com"  # anonymize
    user.hashed_password = dummy_password
    
    await session.commit()
    logger.info(f"User account {user_id} deactivated")


async def change_password(session: AsyncSession, user_id: str, old_password: str, new_password: str) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AuthenticationFailed("User not found.")

    if not verify_password(old_password, user.hashed_password):
        raise AuthenticationFailed("Old password is incorrect.")

    user.hashed_password = hash_password(new_password)
    await session.commit()
    logger.info(f"Password updated for user {user_id}")

