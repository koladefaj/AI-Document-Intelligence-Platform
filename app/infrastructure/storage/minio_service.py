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
    
    Dev Note: This allows the application to be 'Cloud Ready'. 
    You can swap MinIO for AWS S3 by simply changing the environment variables.
    """
    def __init__(self):
        # Client initialization is synchronous
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket = settings.minio_bucket

    async def upload(self, file_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
        """
        Uploads a file to the MinIO bucket.
        
        Dev Note: We use 'file_id' as the Object Name in MinIO to ensure 
        consistency with the database and avoid issues with special characters in filenames.
        """
        try:
            self.ensure_bucket_exists(self.bucket)
            
            # Wrap bytes in a stream for the MinIO SDK
            buffer = BytesIO(file_bytes)

            # Dev Note: We store using 'file_id' (the UUID) so get_file_path can find it easily
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=file_id, 
                data=buffer,
                length=len(file_bytes),
                content_type=content_type
            )
            
            logger.info(f"MinIO: Successfully uploaded {file_id} ({file_name})")
            return f"https://{settings.minio_endpoint}/{self.bucket}/{file_id}"
            
        except Exception as e:
            logger.error(f"MinIO Upload Error: {str(e)}")
            raise

    async def get_file_path(self, file_id: str) -> str:
        """
        Provides a local filesystem path for the AI processor to read.
        
        Workflow:
        1. Checks /tmp cache to avoid redundant downloads.
        2. If missing, streams the object from MinIO to /tmp.
        """
        temp_path = f"/tmp/{file_id}"
        
        # Performance Check: Don't re-download if the worker already has it
        if os.path.exists(temp_path):
            logger.debug(f"MinIO Cache: File {file_id} already exists in /tmp")
            return temp_path
    
        try:
            logger.info(f"MinIO: Downloading {file_id} to {temp_path} for processing")
            # fget_object downloads the file directly to the specified path
            self.client.fget_object(self.bucket, file_id, temp_path)
            return temp_path
        except Exception as e:
            logger.error(f"MinIO Download Error for {file_id}: {str(e)}")
            raise

    def ensure_bucket_exists(self, bucket_name: str):
        """Standard check-and-create logic for the storage container."""
        if not self.client.bucket_exists(bucket_name):
            logger.info(f"MinIO: Creating missing bucket: {bucket_name}")
            self.client.make_bucket(bucket_name)