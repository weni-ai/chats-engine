from django.urls import include, path

from chats.apps.api.v1.routers import router
from chats.apps.api.v1.prometheus.views import metrics_view

urlpatterns = [
    path("", include(router.urls)),
    path("metrics/", metrics_view, name="metrics_view"),
]
