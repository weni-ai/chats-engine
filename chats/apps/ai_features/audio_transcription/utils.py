import io
import logging
import requests

from pydub import AudioSegment

logger = logging.getLogger(__name__)


def get_audio_duration_seconds(media) -> float | None:
    """
    Get the duration of an audio file in seconds.

    Args:
        media: MessageMedia instance with audio content

    Returns:
        Duration in seconds, or None if unable to determine
    """
    try:
        # Try to get audio from file or URL
        if media.media_file:
            audio = AudioSegment.from_file(media.media_file)
        elif media.media_url:
            response = requests.get(media.media_url, timeout=30)
            response.raise_for_status()
            audio_bytes = io.BytesIO(response.content)
            audio = AudioSegment.from_file(audio_bytes)
        else:
            logger.warning("Media %s has no file or URL", media.uuid)
            return None

        # pydub returns duration in milliseconds
        duration_seconds = len(audio) / 1000.0
        return duration_seconds

    except Exception as e:
        logger.error(
            "Error getting audio duration for media %s: %s",
            media.uuid,
            str(e),
        )
        return None
