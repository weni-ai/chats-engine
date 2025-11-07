from django.urls import include, path


from chats.apps.api.v2.routers import router


urlpatterns = [
    path("external/", include("chats.apps.api.v2.external.urls")),
    path("", include(router.urls)),
]
