import uuid
import os
import logging
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.api.v1.websocket_manager import manager
from app.infrastructure.logging import setup_logging, request_id_var
from app.api.v1.router import router as v1_router
from app.core.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Initialize centralized logging configuration
setup_logging()
logger = logging.getLogger(__name__)

allowed = os.getenv("ALLOWED_HOSTS", "*").split(",")

app = FastAPI(
    title="Document Intelligence Backend",
    description="""
AI-powered document analysis service using Gemini and Ollama.

**Supported Document Formats:**
- PDF (.pdf)
- Word Documents (.docx, .doc)
- Excel Spreadsheets (.xlsx, .xls)
- CSV (.csv)
- Plain Text (.txt)

**Features:**
- Extract text and metadata from supported documents
- Analyze content and generate insights
- Supports scanned PDFs via OCR
""",
    version="1.0.0"
)


# --- 1. RATE LIMITING ---
# Dev Note: Limits requests to prevent API abuse. 
# Configuration is handled in app/core/limiter.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- 2. SECURITY MIDDLEWARES ---

# Dev Note: TrustedHostMiddleware prevents HTTP Host Header attacks.
# In Docker/Production, ensure 'backend' or your domain is in this list.
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=allowed
)

# CORS Configuration
# Dev Note: When running in Docker with a Frontend (e.g., React/Next.js), 
# ensure the frontend's container name or URL is added here.
origins = [
    "http://localhost:8000",
    "http://localhost:3000", # Common React port
    "https://your-frontend.up.railway.app",
]

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
        
        # Security Best Practices:
        # 1. Trace the request in headers
        # 2. Prevent MIME type sniffing (security)
        # 3. Prevent Clickjacking (security)
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
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    Real-time updates for document processing.
    The task_id links the WebSocket to the Celery worker's progress.
    """
    await manager.connect(task_id, websocket)
    logger.info(f"WebSocket connection established for task: {task_id}")
    
    try:
        while True:
            # Keep-alive loop
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected gracefully for task {task_id}")
        manager.disconnect(task_id)
    except Exception as e:
        logger.error(f"Unexpected WebSocket error for task {task_id}: {str(e)}")
        manager.disconnect(task_id)

@app.get("/healthy", status_code=200)
def health_check(request: Request):
    """Standard health check for Docker/Kubernetes liveness probes."""
    return {
        "status": "online", 
        "request_id": request.state.request_id,
        "environment": "docker-container"
    }
