import logging
import os
import warnings
from celery import Celery
from app.infrastructure.config import settings

# --- WARNING SUPPRESSION ---
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=FutureWarning, module="llama_index")
os.environ["C_FORCE_ROOT"] = "true"

# Initialize logger for Celery startup events
logger = logging.getLogger(__name__)

# --- CELERY INSTANCE ---
celery_app = Celery(
    "document_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.document_worker"]
)

# --- ADVANCED CONFIGURATION ---
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Prevents tasks from being lost if the worker crashes mid-process
    task_acks_late=True, 
    worker_prefetch_multiplier=1,
    # Increased visibility timeout (2 hours) to handle very large documents without re-queuing
    broker_transport_options={'visibility_timeout': 7200},
    result_expires=3600, # Clean up results after 1 hour
    # Fix for Celery 6.0 deprecation warning
    broker_connection_retry_on_startup=True,
)


try:
    celery_app.control.inspect().ping()
    logger.info("Celery: Successfully connected to Redis broker.")
except Exception:
    logger.warning("Celery: Broker connection not verified yet. (Expected during initial Docker boot)")
