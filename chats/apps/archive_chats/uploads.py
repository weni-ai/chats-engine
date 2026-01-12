ARCHIVED_CONVERSATIONS_PREFIX = "archived_conversations"


def upload_to(instance, filename):
    room = instance.room
    project_uuid = room.queue.sector.project.uuid
    room_uuid = room.uuid

    return f"{ARCHIVED_CONVERSATIONS_PREFIX}/{project_uuid}/{room_uuid}/{filename}"


def media_upload_to(instance, filename):
    room = instance.room
    project_uuid = room.queue.sector.project.uuid
    room_uuid = room.uuid

    return (
        f"{ARCHIVED_CONVERSATIONS_PREFIX}/{project_uuid}/{room_uuid}/media/{filename}"
    )
