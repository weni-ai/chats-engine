from django.db.models import TextChoices


class BulkMessageSendRoomStatus(TextChoices):
    ONGOING = "ongoing"
    WAITING = "waiting"
