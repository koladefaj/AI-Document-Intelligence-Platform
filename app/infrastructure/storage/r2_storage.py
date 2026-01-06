import os
import logging
from io import BytesIO
import boto3

from app.infrastructure.config import settings
from app.domain.services.storage_interface import StorageInterface

logger = logging.getLogger(__name__)

class R2Storage(StorageInterface):
    """
    Cloudflare R2 storage adapter (S3 compatible).
    Used in production (Railway).
    """

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url = settings.s3_endpoint,
            aws_access_key_id = settings.s3_access_key,
            aws_secret_key = settings.s3_secret_key,
            region_name = settings.s3_region
        )
        self.bucket = settings.s3_bucket

    async def upload(self, file_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
        
        try: 
            buffer = BytesIO(file_bytes)

            self.client.put_object(
                Bucket = self.bucket,
                Key = file_id,
                Body=buffer,
                ContentType=content_type
            )

            logger.info(f'R2: Uploaded {file_id} ({file_id})')

            return file_id
        
        except Exception as e:
            logger.error(f"R2 Upload Error: {str(e)}")
            raise
    
    async def get_file_path(self, file_id: str):
        temp_path = f"/tmp/{file_id}"

        if os.path.exists(temp_path):
            return temp_path
        
        try:
            logger.info(f"R2: Downloading {file_id} to {temp_path}")

            self.client.download_file(
                Bucket=self.bucket,
                Key=file_id,
                Filename=temp_path
            )

            return temp_path
        
        except Exception as e:
            logger.error(f"R2 Download Error: {str(e)}")
            raise
