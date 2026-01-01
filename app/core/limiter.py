import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.infrastructure.config import settings

# Initialize logger
logger = logging.getLogger(__name__)

# --- RATE LIMITER CONFIGURATION ---
# key_func=get_remote_address: Identifies users by their IP address.
#
# Dev Note: In a Docker/Proxy setup (like Nginx), ensure you have 
# 'Forwarded-For' headers configured, or the limiter will see 
# the proxy's IP instead of the user's.
limiter = Limiter(
    key_func=get_remote_address,
    # This points to your Redis instance so limits are shared across all Docker containers
    storage_uri=f"{settings.redis_url}",
    strategy="fixed-window", # Common strategies: 'fixed-window', 'moving-window'
)

def init_limiter_error_handlers(app):
    """
    Optional: Registers a custom error handler to return 
    a clean JSON response when a user is rate-limited.
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from slowapi.errors import RateLimitExceeded

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        logger.warning(f"Rate limit exceeded by IP: {request.client.host}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
        )