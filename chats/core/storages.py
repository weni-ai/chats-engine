# chats/core/storages.py
from storages.backends.s3boto3 import S3Boto3Storage
from typing import Optional


class BaseS3Storage(S3Boto3Storage):
    """
    Base class for S3 storage with configurable location.
    """
    
    storage_location = None
    
    def __init__(self, location: Optional[str] = None, **kwargs):
        self._custom_location = location
        super().__init__(**kwargs)
    
    def get_default_settings(self):
        default_settings = super().get_default_settings()
        location = self._custom_location or self.storage_location or ""
        default_settings["location"] = location
        return default_settings
    
    def get_download_url(self, file_path: str, expiration: int = 604800) -> str:
        """
        Generate a pre-signed URL for download.
        
        Args:
            file_path: Path to the file in S3
            expiration: URL expiration time in seconds (default: 7 days)
        
        Returns:
            Pre-signed URL string
        """
        return self.url(file_path, expire=expiration)


class ExcelStorage(BaseS3Storage):
    """Storage for dashboard Excel files"""
    storage_location = "dashboard_data/excel"


class ReportsStorage(BaseS3Storage):
    """Storage for report files (CSV, XLSX, ZIP)"""
    storage_location = "reports"