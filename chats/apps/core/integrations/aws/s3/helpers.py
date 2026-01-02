from urllib.parse import urlparse


def is_file_in_the_same_bucket(url: str, bucket_name: str) -> bool:
    """
    Check if the file is in the same bucket as the given bucket name.
    """
    # AWS Docs: https://docs.aws.amazon.com/general/latest/gr/s3.html
    # This cover most cases of S3 URLs, but not all.
    # For our current use case, this is enough.
    parsed = urlparse(url)

    # Handle s3://bucket/key
    if parsed.scheme == "s3":
        return parsed.netloc.lower() == bucket_name.lower()

    host = parsed.netloc.lower()
    bucket = bucket_name.lower()

    # Virtual-hosted–style (including regional, dualstack)
    if host == f"{bucket}.s3.amazonaws.com":
        return True

    if host.startswith(f"{bucket}.s3.") and host.endswith(".amazonaws.com"):
        return True

    # Path-style: s3.<region>.amazonaws.com/bucket/key
    if host.startswith("s3.") and host.endswith(".amazonaws.com"):
        path_bucket = parsed.path.lstrip("/").split("/", 1)[0]
        return path_bucket == bucket

    return False
