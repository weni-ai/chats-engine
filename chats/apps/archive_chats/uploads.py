def upload_to(instance, filename):
    room = instance.room
    project_uuid = room.queue.sector.project.uuid
    room_uuid = room.uuid

    return f"archived_conversations/{project_uuid}/{room_uuid}/{filename}"
