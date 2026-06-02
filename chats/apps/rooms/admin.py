from django.contrib import admin

from chats.apps.dashboard.models import RoomMetrics
from chats.apps.rooms.models import Room, RoomNote

# Register your models here.

admin.site.register(Room)
admin.site.register(RoomMetrics)
admin.site.register(RoomNote)
