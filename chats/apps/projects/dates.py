from datetime import datetime
import pytz
import re


def parse_date_with_timezone(
    date_str: str, project_timezone: str, is_end_date: bool = False
) -> datetime:
    """
    Parse date string with different formats and handle timezone conversion.

    Args:
        date_str: Date string in various formats (YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, etc.)
        project_timezone: Project's timezone key
        is_end_date: If True, sets time to 23:59:59, otherwise 00:00:00

    Returns:
        datetime object with project timezone
    """

    if not date_str:
        return None

    tz = pytz.timezone(project_timezone)

    # Check if it's just a date (YYYY-MM-DD)
    date_only_pattern = r"^\d{4}-\d{2}-\d{2}$"
    if re.match(date_only_pattern, date_str):
        time_str = " 23:59:59" if is_end_date else " 00:00:00"
        naive_dt = datetime.strptime(date_str + time_str, "%Y-%m-%d %H:%M:%S")
        return tz.localize(naive_dt)

    # Try to parse as ISO datetime format with timezone
    try:
        # First try to parse as timezone-aware datetime
        if (
            "+" in date_str
            or date_str.endswith("Z")
            or re.search(
                r"[+-]\d{2}:\d{2}$", date_str
            )  # Matches formats like -03:00, +05:30
            or re.search(r"[+-]\d{4}$", date_str)  # Matches formats like -0300, +0530
        ):
            # Handle timezone-aware formats
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # Convert to project timezone
            return dt.astimezone(tz)
    except ValueError:
        pass

    # Try to parse as naive datetime formats
    try:
        datetime_formats = [
            "%Y-%m-%dT%H:%M:%S",  # 2025-01-01T00:00:00
            "%Y-%m-%dT%H:%M:%S.%f",  # 2025-01-01T00:00:00.000000
            "%Y-%m-%d %H:%M:%S",  # 2025-01-01 00:00:00
            "%Y-%m-%d %H:%M:%S.%f",  # 2025-01-01 00:00:00.000000
        ]

        naive_dt = None
        for fmt in datetime_formats:
            try:
                naive_dt = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue

        if naive_dt is not None:
            # Localize with project timezone
            return tz.localize(naive_dt)

    except ValueError:
        pass

    time_str = " 23:59:59" if is_end_date else " 00:00:00"
    naive_dt = datetime.strptime(date_str + time_str, "%Y-%m-%d %H:%M:%S")

    return tz.localize(naive_dt)
