import logging
from celery import Celery
from app.infrastructure.config import settings

# Initialize logger for Celery startup events
logger = logging.getLogger(__name__)

# --- CELERY INSTANCE ---
# 'document_tasks' is the main namespace for your background jobs.
# broker: Usually Redis (e.g., redis://redis:6379/0) - handles the message queue.
# backend: Usually Redis - stores the task result and status.
celery_app = Celery(
    "document_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# --- ADVANCED CONFIGURATION ---
celery_app.conf.update(
    # Security & Format: JSON is standard and safe for cross-language compatibility
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Timezone Handling: Always keep servers on UTC to avoid 'time travel' bugs
    timezone="UTC",
    enable_utc=True,

    # --- RELIABILITY SETTINGS (Dev Note: Critical for 2026 Production) ---
    # Prevents tasks from being lost if the worker crashes mid-process
    task_acks_late=True, 
    
    # Ensures the worker only takes one task at a time (better for heavy AI workloads)
    worker_prefetch_multiplier=1,
    
    # Optional: Automatically discover tasks in the workers folder
    # celery_app.autodiscover_tasks(['app.workers']),
)

# Dev Note: This check helps a developer verify Redis connectivity during startup
try:
    celery_app.control.inspect().ping()
    logger.info("Celery: Successfully connected to Redis broker.")
except Exception:
    logger.warning("Celery: Broker connection not verified yet. (Expected during initial Docker boot)")