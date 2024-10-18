from storages.backends.s3boto3 import S3Boto3Storage


class PrivateMediaStorage(S3Boto3Storage):
    file_overwrite = False
    custom_domain = False
    querystring_auth = True
