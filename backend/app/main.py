import uuid
import os
import logging
import warnings
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

# --- WARNING SUPPRESSION (CRITICAL FOR CLEAN LOGS) ---
# Suppress Pydantic v2 validation warnings from dependencies
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
# Suppress LlamaIndex/Google deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="llama_index")
# Suppress Celery root warnings
os.environ["C_FORCE_ROOT"] = "true"

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.api.v1.websocket_manager import manager
from app.infrastructure.logging import setup_logging, request_id_var
from app.api.v1.router import router as v1_router
from app.core.limiter import limiter
from app.infrastructure.config import settings
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Initialize centralized logging configuration
setup_logging()
logger = logging.getLogger(__name__)

allowed = os.getenv("ALLOWED_HOSTS", "*").split(",")

app = FastAPI(
    title="Document Intelligence Backend",
    description="""
AI-powered document analysis and **RAG (Retrieval-Augmented Generation)** service using Gemini and Ollama.

**Features:**
- **RAG Engine**: Semantic search and contextual Q&A on your documents.
- **ORM Vector Store**: High-performance HNSW-indexed embeddings in Postgres.
- **Cost Optimization**: SHA-256 de-duplication to skip redundant AI processing.
- **Resource Monitoring**: Token-based usage tracking per user.
- **Storage Flexibility**: Support for Local, MinIO, and Cloudflare R2 storage.
- **OCR Support**: Extract text from scanned PDFs and images.
""",
    version="1.0.0"
)


# --- 1. RATE LIMITING ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- 2. SECURITY MIDDLEWARES ---

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=allowed
)

# CORS Configuration
origins = settings.allowed_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# --- 3. REQUEST TRACING & SECURITY HEADERS ---
@app.middleware("http")
async def security_and_tracing_middleware(request: Request, call_next):
    """
    Middleware to assign a unique Request ID to every incoming call.
    This ID is propagated to logs and the Celery worker for end-to-end tracing.
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # ContextVar for logging (allows logs to show request_id automatically)
    token = request_id_var.set(request_id)

    try:
        response = await call_next(request)
        
        # Add security headers to the response
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        
        return response
    finally:
        # Clear context after request finishes
        request_id_var.reset(token)

# --- 4. ROUTES & WEBSOCKETS ---
app.include_router(v1_router, prefix="/api/v1")

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str, token: str = None):
    """
    Real-time updates for document processing with Token Auth.
    """
    from jose import jwt, JWTError
    from app.infrastructure.config import settings

    # 1. Validate Token from Query Param
    if not token:
        await websocket.close(code=4001)
        return
    
    try:
        # Decode but we just need to know it's valid
        jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        await websocket.close(code=4001)
        return

    # 2. Connect if valid
    await manager.connect(task_id, websocket)
    logger.info(f"WS: Secure connection for task: {task_id}")
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WS: Disconnected task {task_id}")
        manager.disconnect(task_id)
    except Exception as e:
        logger.error(f"WS Error {task_id}: {str(e)}")
        manager.disconnect(task_id)

@app.get("/healthy", status_code=200)
def health_check(request: Request):
    """Standard health check for Docker/Kubernetes liveness probes."""
    return {
        "status": "online", 
        "request_id": request.state.request_id,
        "environment": "docker-container"
    }
