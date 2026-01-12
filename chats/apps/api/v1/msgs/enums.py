from django.db.models import TextChoices


class MessageMediaContentTypesFilterParams(TextChoices):
    AUDIO = "audio"  # Only audio files are returned
    MEDIA = "media"  # Audio and video files are returned
    DOCUMENTS = "documents"  # Documents that are not audio or video
