from minio import Minio
from io import BytesIO
from app.infrastructure.config import settings
from app.domain.services.storage_interface import StorageInterface

class MinioStorage(StorageInterface):
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket = settings.minio_bucket

    async def upload_file(self, file_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
        """ Upload a file """
        self.ensure_bucket_exists(self.bucket)

        buffer = BytesIO(file_bytes)

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=file_name,
            data=buffer,
            length=len(file_bytes),
            content_type=content_type
        )

        return f"https://{settings.minio_endpoint}/{self.bucket}/{file_id}"

    def ensure_bucket_exists(self, bucket_name: str) -> bool:
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

