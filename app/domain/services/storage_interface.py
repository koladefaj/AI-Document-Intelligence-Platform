from typing import Protocol
from abc import ABC, abstractmethod

class StorageInterface(Protocol):
    async def upload(self, file_id: str, file_bytes: bytes, content_type: str) -> str:
        """ Upload a file and return its url """
        pass

class BaseStorage(ABC):
    async def upload(self, file_id: str, file_bytes: bytes, content_type: str) -> str:
        """ Upload a file and return its url"""
        pass