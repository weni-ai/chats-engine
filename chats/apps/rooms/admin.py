from django.contrib import admin

from chats.apps.rooms.models import Room

from chats.apps.dashboard.models import RoomMetrics

# Register your models here.

admin.site.register(Room)
admin.site.register(RoomMetrics)
