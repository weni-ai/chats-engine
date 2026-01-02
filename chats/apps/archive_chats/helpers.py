from urllib.parse import urlparse

from django.utils.crypto import get_random_string


def get_filename_from_url(url: str) -> str:
    """
    Get the filename from a url.
    """
    parsed_url = urlparse(url)

    return parsed_url.path.split("/")[-1]


def generate_unique_filename(
    original_filename: str, used_filenames: set[str], max_attempts: int = 5
) -> str:
    """
    Generate a unique filename based on the original filename.
    """
    if original_filename not in used_filenames:
        return original_filename

    parts = original_filename.split(".")

    extension = parts[-1]
    name = ".".join(parts[:-1])

    new_filename = f"{name}_{get_random_string(8)}.{extension}"

    for i in range(max_attempts):
        if new_filename not in used_filenames:
            return new_filename

        new_filename = f"{name}_{get_random_string(8)}.{extension}"

    raise ValueError(
        f"Failed to generate a unique filename after {max_attempts} attempts"
    )
