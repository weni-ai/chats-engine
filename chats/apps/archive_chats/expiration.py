from datetime import datetime, timezone, timedelta


def calculate_archive_task_expiration_dt(max_hour: str) -> datetime:
    """
    Get the expiration date and time for the archive chats task.
    """
    try:
        max_hour_dt = datetime.strptime(max_hour, "%H:%M")
    except ValueError:
        raise ValueError(
            f"Invalid max hour: {max_hour}. Should be in the format HH:MM (UTC-0)"
        )

    now = datetime.now(timezone.utc)

    expiration_dt = datetime.combine(now.date(), max_hour_dt.time())

    if expiration_dt < now:
        expiration_dt += timedelta(days=1)

    return expiration_dt
