from fastapi import APIRouter
from app.api.v1.routes import auth, documents, tasks

# The base router for the entire application
# If you add more versions in the future, you would create a 'v2' router here.
router = APIRouter()

# --- v1 ROUTE INCLUSIONS ---
# We use prefixes and tags here to ensure the Swagger/OpenAPI documentation
# is organized and easy for frontend developers to read.

# Authentication: /auth/login, /auth/register
router.include_router(
    auth.router, 
    prefix="/v1"
)

# Tasks: /tasks/{task_id}
router.include_router(
    tasks.router, 
    prefix="/v1"
)

# Documents: /documents/upload
router.include_router(
    documents.router, 
    prefix="/v1"
)