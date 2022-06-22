from django.urls import path, include

from chats.apps.api.v1.routers import router


urlpatterns = [
    path("", include(router.urls)),
]
