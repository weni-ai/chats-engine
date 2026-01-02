ROOT_ARCHIVED_CONVERSATIONS_PATH = "archived_conversations"


def get_room_archived_conversation_path(room):
    project_uuid = room.queue.sector.project.uuid
    room_uuid = room.uuid

    return f"{ROOT_ARCHIVED_CONVERSATIONS_PATH}/{project_uuid}/{room_uuid}"


def upload_to(instance, filename):
    room = instance.room

    return f"{get_room_archived_conversation_path(room)}/{filename}"


def get_media_upload_to(instance, filename):
    room = instance.room

    return f"{get_room_archived_conversation_path(room)}/media/{filename}"
