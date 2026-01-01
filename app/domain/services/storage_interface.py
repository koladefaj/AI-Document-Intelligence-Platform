from typing import Protocol
from abc import ABC, abstractmethod

class StorageInterface(Protocol):
    """
    The Protocol defines the expected behavior for storage providers.
    
    This is used by the Dependency Injection system to allow 
    hot-swapping between LocalStorage and MinioStorage without 
    changing any business logic in the API or Workers.
    """
    async def upload(self, file_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
        """Uploads a file and returns the accessible URL or path."""
        ...

    async def get_file_path(self, file_id: str) -> str:
        """
        Resolves the file's location on the local filesystem.
        If the file is in the cloud (MinIO), it is downloaded to /tmp first.
        """
        ...


class BaseStorage(ABC):
    """
    Optional abstract base class for shared storage logic.
    Provides a template for implementing new storage adapters.
    """
    @abstractmethod
    async def upload(self, file_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
        pass

    @abstractmethod
    async def get_file_path(self, file_id: str) -> str:
        """Returns the local string path to the file."""
        pass