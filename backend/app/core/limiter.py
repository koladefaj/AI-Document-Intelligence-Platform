import logging
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.infrastructure.config import settings

# Initialize logger
logger = logging.getLogger(__name__)

storage_uri = settings.redis_url if os.getenv("ENV") != "testing" else "memory://"
IS_TESTING = os.getenv("ENV") == "testing"

# --- RATE LIMITER CONFIGURATION ---
# key_func=get_remote_address: Identifies users by their IP address.
#
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"{storage_uri}",
    strategy="fixed-window",
    enabled=not IS_TESTING
)

def init_limiter_error_handlers(app):
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
