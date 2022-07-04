# chat/urls.py
from django.urls import path

from chats.apps.rooms import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<str:room_name>/", views.room, name="room"),
]
