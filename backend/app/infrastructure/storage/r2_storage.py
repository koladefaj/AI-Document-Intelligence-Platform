import os
import logging
import asyncio
import tempfile
from pathlib import Path
from io import BytesIO
import boto3

from app.infrastructure.config import settings
from app.domain.services.storage_interface import StorageInterface

logger = logging.getLogger(__name__)

class R2Storage(StorageInterface):
    """
    Cloudflare R2 storage adapter (S3 compatible).
    """

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url = settings.s3_endpoint,
            aws_access_key_id = settings.s3_access_key,
            aws_secret_access_key = settings.s3_secret_key,
            region_name = settings.s3_region
        )
        self.bucket = settings.s3_bucket
        # Use system temp dir for cross-platform support (Windows/Linux)
        self.temp_dir = Path(tempfile.gettempdir())

    async def upload(self, file_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
        
        try: 
            buffer = BytesIO(file_bytes)

            # Offload blocking boto3 call to a thread
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket,
                Key=file_id,
                Body=buffer,
                ContentType=content_type
            )

            logger.info(f'R2: Uploaded {file_id}')

            return file_id
        
        except Exception as e:
            logger.error(f"R2 Upload Error: {str(e)}")
            raise
    
    async def get_file_path(self, file_id: str) -> str:
        temp_path = str(self.temp_dir / file_id)

        if os.path.exists(temp_path):
            return temp_path
        
        try:
            logger.info(f"R2: Downloading {file_id} to {temp_path}")

            # Offload blocking boto3 call to a thread
            await asyncio.to_thread(
                self.client.download_file,
                Bucket=self.bucket,
                Key=file_id,
                Filename=temp_path
            )

            return temp_path
        
        except Exception as e:
            logger.error(f"R2 Download Error: {str(e)}")
            raise
        
    async def delete(self, file_id: str) -> bool:
        try:
            logger.info(f"R2: Deleting {file_id}")
            
            # Offload blocking boto3 call to a thread
            await asyncio.to_thread(
                self.client.delete_object,
                Bucket=self.bucket,
                Key=file_id
            )
            
            # Also remove from local cache if exists
            temp_path = str(self.temp_dir / file_id)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return True
        except Exception as e:
            logger.error(f"R2 Delete Error: {str(e)}")
            return False
