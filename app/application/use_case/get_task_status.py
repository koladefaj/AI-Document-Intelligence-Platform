from app.infrastructure.queue.celery_app import celery_app
from celery.result import AsyncResult
from fastapi import Depends
from app.dependencies import get_task_queue

def get_task_status(task_id: str, queue = Depends(get_task_queue)):
    result = AsyncResult(task_id, app=queue)

    return {
        "task_id":task_id,
        "status":result.state,
        "result":result.result if result.successful() else None,
        "is_completed": result.successful(),
        "is_failed": result.failed(),
        "is_pending": result.status in ["PENDING", "STARTED"]
    }
