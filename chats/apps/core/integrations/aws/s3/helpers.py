import boto3
from django.conf import settings


def get_presigned_url(object_key: str) -> str:
    return boto3.client("s3").generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": object_key},
        ExpiresIn=3600,
    )
