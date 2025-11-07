from django.urls import include, path


from chats.apps.api.v2.routers import router


urlpatterns = [
    path("", include(router.urls)),
]
