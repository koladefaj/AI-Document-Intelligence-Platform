import logging
from celery.result import AsyncResult
from app.infrastructure.queue.celery_app import celery_app

# Initialize logger for tracking task lifecycle
logger = logging.getLogger(__name__)

def get_task_status(task_id: str) -> dict:
    """
    Fetches the current state and result of a background Celery task.
    
    This is called by the GET /tasks/{task_id} endpoint to inform
    the user if their document is still being analyzed.
    """
    try:
        # We bind the task_id to our specific celery_app instance
        # to ensure we're looking at the correct Redis result backend.
        result = AsyncResult(task_id, app=celery_app)

        # Standardizing the response format for the frontend
        status_data = {
            "task_id": task_id,
            "status": result.state,  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
            "is_completed": result.successful(),
            "is_failed": result.failed(),
            # We consider the task 'in progress' if it hasn't finished or failed yet
            "is_pending": result.status in ["PENDING", "STARTED", "RETRY"],
            "result": None,
            "error": None
        }

        # If the task finished successfully, result.result contains 
        # the dict returned by the worker's process() method.
        if result.ready():
            if result.successful():
                status_data["result"] = result.result
                logger.info(f"Task {task_id} completed successfully.")
            else:
                # If it failed, result.result contains the Exception message
                status_data["error"] = str(result.result)
                logger.warning(f"Task {task_id} failed: {status_data['error']}")

        return status_data

    except Exception as e:
        logger.error(f"Error fetching status for task {task_id}: {str(e)}")
        # Return a safe fallback so the API doesn't crash
        return {
            "task_id": task_id,
            "status": "UNKNOWN",
            "error": "Could not connect to the task backend."
        }