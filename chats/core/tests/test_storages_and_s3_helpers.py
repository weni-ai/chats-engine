from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from chats.apps.core.integrations.aws.s3.helpers import (
    get_object_key,
    get_presigned_url,
)
from chats.core.storages import (
    BaseS3Storage,
    ExcelStorage,
    ReportsStorage,
    RoomExportStorage,
)


class GetObjectKeyTests(SimpleTestCase):
    def test_strips_leading_slash_from_path(self):
        self.assertEqual(
            get_object_key("https://bucket.s3.amazonaws.com/folder/file.txt"),
            "folder/file.txt",
        )

    def test_handles_s3_scheme_url(self):
        self.assertEqual(get_object_key("s3://bucket/path/to/object"), "path/to/object")


class GetPresignedUrlTests(SimpleTestCase):
    @override_settings(AWS_STORAGE_BUCKET_NAME="test-bucket")
    @patch("chats.apps.core.integrations.aws.s3.helpers.boto3.client")
    def test_generates_presigned_url_for_object_key(self, mock_boto_client):
        s3_client = MagicMock()
        s3_client.generate_presigned_url.return_value = "https://signed.example/file"
        mock_boto_client.return_value = s3_client

        url = get_presigned_url("reports/file.csv")

        self.assertEqual(url, "https://signed.example/file")
        mock_boto_client.assert_called_once_with("s3")
        s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "reports/file.csv"},
            ExpiresIn=3600,
        )


class BaseS3StorageTests(SimpleTestCase):
    @patch("storages.backends.s3boto3.S3Boto3Storage.__init__", return_value=None)
    def test_init_stores_custom_location(self, _mock_super_init):
        storage = BaseS3Storage(location="custom/path")

        self.assertEqual(storage._custom_location, "custom/path")

    @patch.object(BaseS3Storage, "__init__", lambda self, **kwargs: None)
    def test_get_default_settings_uses_custom_location(self):
        storage = BaseS3Storage()
        storage._custom_location = "custom/path"
        storage.storage_location = "ignored"

        with patch(
            "storages.backends.s3boto3.S3Boto3Storage.get_default_settings",
            return_value={},
        ):
            settings = storage.get_default_settings()

        self.assertEqual(settings["location"], "custom/path")

    @patch.object(BaseS3Storage, "__init__", lambda self, **kwargs: None)
    def test_get_default_settings_falls_back_to_storage_location(self):
        storage = BaseS3Storage()
        storage._custom_location = None
        storage.storage_location = "reports"

        with patch(
            "storages.backends.s3boto3.S3Boto3Storage.get_default_settings",
            return_value={},
        ):
            settings = storage.get_default_settings()

        self.assertEqual(settings["location"], "reports")

    @patch.object(BaseS3Storage, "__init__", lambda self, **kwargs: None)
    def test_get_download_url_uses_storage_url(self):
        storage = BaseS3Storage()
        storage.url = MagicMock(return_value="https://download.example/file")

        url = storage.get_download_url("file.csv", expiration=100)

        self.assertEqual(url, "https://download.example/file")
        storage.url.assert_called_once_with("file.csv", expire=100)


class SpecializedStorageLocationTests(SimpleTestCase):
    def test_excel_storage_location(self):
        self.assertEqual(ExcelStorage.storage_location, "dashboard_data/excel")

    def test_reports_storage_location(self):
        self.assertEqual(ReportsStorage.storage_location, "reports")

    def test_room_export_storage_location(self):
        self.assertEqual(RoomExportStorage.storage_location, "room_exports")
