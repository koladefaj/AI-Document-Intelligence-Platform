from fastapi import APIRouter
from app.api.v1.routes import auth, documents, tasks

# The base router for the entire application
# If you add more versions in the future, you would create a 'v2' router here.
router = APIRouter()


# Authentication: /auth/login, /auth/register
router.include_router(
    auth.router
)

# Documents: /documents/upload
router.include_router(
    documents.router
)

# Tasks: /tasks/{task_id}
router.include_router(
    tasks.router
)