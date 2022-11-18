from channels.db import database_sync_to_async

from chats.apps.rooms.models import Room


class WSJoinValidator:
    def __init__(self, group_name, group_id, project_uuid, user_permission):
        self.user_permission = user_permission
        self.group_name = group_name
        self.group_id = group_id
        self.project_uuid = project_uuid

    async def validate(self):
        return await getattr(self, f"validate_{self.group_name}")()

    @database_sync_to_async
    def validate_queue(self):
        return self.user_permission.is_agent(self.group_id)

    @database_sync_to_async
    def validate_room(self):
        room = Room.objects.get(pk=self.group_id)
        if room.user == self.user_permission.user:
            return True
        if room.user is not None:
            return False
        return self.user_permission.is_agent(str(room.queue.pk))

    @database_sync_to_async
    def validate_user(self):
        return self.group_id == self.user_permission.user.id
