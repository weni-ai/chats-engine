from storages.backends.s3boto3 import S3Boto3Storage


class ExcelStorage(S3Boto3Storage):  # pragma: no cover
    def get_default_settings(self):
        default_settings = super().get_default_settings()
        default_settings["location"] = f"apptypes/aa"
        return default_settings
