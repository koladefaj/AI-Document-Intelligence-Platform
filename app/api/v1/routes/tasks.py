from fastapi import APIRouter
from app.application.use_case.get_task_status import get_task_status

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/{task_id}")
def task_status(task_id: str):
    response = get_task_status(task_id)
    return response
