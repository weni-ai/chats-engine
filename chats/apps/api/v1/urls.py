from django.urls import include, path

from chats.apps.api.v1.rooms.viewsets import RoomsReportViewSet
from chats.apps.api.v1.dashboard.viewsets import ModelFieldsViewSet, ReportFieldsValidatorViewSet
from chats.apps.api.v1.routers import router

urlpatterns = [
    path("rooms/report/", RoomsReportViewSet.as_view(), name="rooms_report"),
    path("model-fields/", ModelFieldsViewSet.as_view(), name="model-fields"),
    path("custom-report/", ReportFieldsValidatorViewSet.as_view(), name="custom-report"),
    path("", include(router.urls)),
]
