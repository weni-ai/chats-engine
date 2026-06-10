from django.db.models import TextChoices


class RoomFeedbackMethods(TextChoices):
    ROOM_TRANSFER = "rt"
    EDIT_CUSTOM_FIELDS = "ecf"
    FLOW_START = "fs"
