import pytest


@pytest.fixture(autouse=True)
def override_settings(settings):
    settings.AWS_STORAGE_BUCKET_NAME = "test-bucket"
