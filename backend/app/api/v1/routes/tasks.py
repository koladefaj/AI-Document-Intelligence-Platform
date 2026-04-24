import logging
from fastapi import APIRouter, HTTPException, status, Depends
from app.infrastructure.auth.dependencies import get_current_user
from app.application.use_case.get_task_status import get_task_status

# Initialize logger for task tracking
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tasks", 
    tags=["tasks"]
)

@router.get("/{task_id}")
async def check_task_status(task_id: str, user = Depends(get_current_user)):
    """
    Fetches the current state of a background job from the Redis backend.
    
    Returns:
        - PENDING: Task is in the queue.
        - STARTED: Worker has picked up the document.
        - SUCCESS: AI analysis is complete (includes 'result').
        - FAILURE: An error occurred (includes 'error' details).
    """
    try:
        # The use-case handles the connection to the Celery/Redis backend
        status_report = get_task_status(task_id)
        
        # Log only if the task has reached a terminal state
        if status_report.get("is_completed"):
            logger.info(f"Task API: Task {task_id} confirmed SUCCESS.")
        elif status_report.get("is_failed"):
            logger.warning(f"Task API: Task {task_id} confirmed FAILURE.")
            
        return status_report

    except Exception as e:
        logger.error(f"Task API Error: Could not retrieve status for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not reach the task tracking service."
        )