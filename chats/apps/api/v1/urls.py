from django.urls import include, path

from chats.apps.api.v1.dashboard.viewsets import (
    ModelFieldsViewSet,
    ReportFieldsValidatorViewSet,
)
from chats.apps.api.v1.internal.ai_features.views import FeaturePromptsView
from chats.apps.api.v1.rooms.viewsets import RoomsReportViewSet
from chats.apps.api.v1.routers import router

urlpatterns = [
    path("rooms/report/", RoomsReportViewSet.as_view(), name="rooms_report"),
    path(
        "internal/ai_features/prompts/",
        FeaturePromptsView.as_view(),
        name="ai_features_prompts",
    ),
    path(
        "model-fields/",
        ModelFieldsViewSet.as_view({"get": "list"}),
        name="model-fields",
    ),
    path(
        "custom-report/",
        ReportFieldsValidatorViewSet.as_view({"post": "create"}),
        name="custom-report",
    ),
    path("", include(router.urls)),
]
