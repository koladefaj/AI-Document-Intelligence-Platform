import os
import logging
from minio import Minio
from io import BytesIO
from app.infrastructure.config import settings
from app.domain.services.storage_interface import StorageInterface

# Initialize logger
logger = logging.getLogger(__name__)

class MinioStorage(StorageInterface):
    """
    S3-Compatible Storage Provider using MinIO.
    Optimized for Railway and Local Docker environments.
    """
    def __init__(self):
        # IMPORTANT: MinIO SDK expects 'host:port', not 'http://host:port'
        # We strip any protocol prefixes just in case they exist in settings
        clean_endpoint = (
            settings.minio_endpoint
            .replace("https://", "")
            .replace("http://", "")
            .strip("/")
        )

        logger.info(f"MinIO: Initializing client with endpoint: {clean_endpoint}")

        try:
            self.client = Minio(
                clean_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                # secure=True if using port 443/SSL, False for Railway private 9000
                secure=settings.minio_secure 
            )
            self.bucket = settings.minio_bucket
        except Exception as e:
            logger.error(f"MinIO: Failed to initialize client: {str(e)}")
            raise

    async def upload(self, file_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
        """Uploads a file using the file_id as the unique object name."""
        try:
            self.ensure_bucket_exists(self.bucket)
            
            buffer = BytesIO(file_bytes)

            self.client.put_object(
                bucket_name=self.bucket,
                object_name=file_id, 
                data=buffer,
                length=len(file_bytes),
                content_type=content_type
            )
            
            logger.info(f"MinIO: Successfully uploaded {file_id} ({file_name})")

            # Return a formatted URL for reference
            protocol = "https" if settings.minio_secure else "http"
            return f"{protocol}://{settings.minio_endpoint}/{self.bucket}/{file_id}"
            
        except Exception as e:
            logger.error(f"MinIO Upload Error: {str(e)}")
            raise

    async def get_file_path(self, file_id: str) -> str:
        """Downloads file to /tmp for AI processing if not already cached."""
        temp_path = f"/tmp/{file_id}"
        
        if os.path.exists(temp_path):
            logger.debug(f"MinIO Cache: File {file_id} already exists in /tmp")
            return temp_path
    
        try:
            logger.info(f"MinIO: Downloading {file_id} to {temp_path}")
            self.client.fget_object(self.bucket, file_id, temp_path)
            return temp_path
        except Exception as e:
            logger.error(f"MinIO Download Error for {file_id}: {str(e)}")
            raise

    def ensure_bucket_exists(self, bucket_name: str):
        """Ensures the storage bucket is ready for use."""
        try:
            if not self.client.bucket_exists(bucket_name):
                logger.info(f"MinIO: Creating missing bucket: {bucket_name}")
                self.client.make_bucket(bucket_name)
        except Exception as e:
            logger.error(f"MinIO Bucket Error: {str(e)}")
            raise