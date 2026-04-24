import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, patch
import tempfile
import os

patcher = patch("slowapi.extension.Limiter.limit", side_effect=lambda *args, **kwargs: lambda f: f)
patcher.start()

from app.main import app # noqa: E402
from app.infrastructure.db.models import Base # noqa: E402
from app.infrastructure.db.session import get_session # noqa: E402
from app.dependencies import get_storage_service # noqa: E402


app.state.limiter_enabled = False


# 1. SETUP TEST DATABASE (In-Memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

@pytest.fixture(scope="session", autouse=True)
def stop_patcher():
    yield
    patcher.stop()

@pytest.fixture(scope="session", autouse=True)
def disable_limiter():
    app.state.limiter_enabled = False
    yield
    

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function", autouse=True)
async def setup_db():
    """Create and drop database tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a clean database session for every test."""
    async with TestingSessionLocal() as session:
        yield session
        try:
            if session.is_active:
                await session.rollback()
        except Exception:
            pass


# 2. MOCK R2 STORAGE SERVICE
class MockR2Storage:
    """
    Mock implementation of R2Storage for testing.
    Mimics the behavior without actually connecting to R2/S3.
    """
    
    def __init__(self):
        self.uploaded_files = {}  # Store uploaded files in memory {file_id: bytes}
        self.bucket = "test-bucket"
        self.client = MagicMock()  # Mock boto3 client
    
    async def upload(self, file_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
        """Mock file upload - stores in memory instead of R2"""
        self.uploaded_files[file_id] = {
            "file_name": file_name,
            "bytes": file_bytes,
            "content_type": content_type
        }
        return file_id
    
    async def get_file_path(self, file_id: str) -> str:
        """Mock file download - creates a temp file instead of downloading from R2"""
        if file_id not in self.uploaded_files:
            raise FileNotFoundError(f"File {file_id} not found in mock storage")
        
        # Create a temporary file with the mock data
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file_id)
        
        with open(temp_path, "wb") as f:
            f.write(self.uploaded_files[file_id]["bytes"])
        
        return temp_path
    
    def clear(self):
        """Clear all uploaded files (useful between tests)"""
        self.uploaded_files.clear()


@pytest.fixture
def mock_storage_service():
    """Creates a mock R2Storage service for testing."""
    mock = MockR2Storage()
    yield mock
    mock.clear()  # Clean up after test


# 3. OVERRIDE FASTAPI DEPENDENCIES
@pytest.fixture(autouse=True)
def override_dependencies(db_session, mock_storage_service):
    """Replaces real dependencies with test mocks in FastAPI."""
    
    # Override database session
    async def _get_test_session():
        yield db_session
    
    # Override storage service
    def _get_mock_storage():
        return mock_storage_service
    
    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[get_storage_service] = _get_mock_storage
    
    yield
    
    # Clean up overrides after test
    app.dependency_overrides.clear()


# 4. ASYNC HTTP CLIENT
@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """The 'browser' that will call your API routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, 
        base_url="http://localhost", 
        headers={"Host": "localhost"}
    ) as ac:
        yield ac