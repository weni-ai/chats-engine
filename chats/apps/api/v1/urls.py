from django.urls import include, path

from chats.apps.api.v1.routers import router

urlpatterns = [
    path("", include(router.urls)),
]
