from django.urls import include, path

from chats.apps.api.v1.dashboard.viewsets import (
    ModelFieldsViewSet,
    ReportFieldsValidatorViewSet,
)
from chats.apps.api.v1.internal.agents.views import AgentDisconnectView
from chats.apps.api.v1.internal.ai_features.views import FeaturePromptsView
from chats.apps.api.v1.rooms.viewsets import RoomsReportViewSet
from chats.apps.api.v1.routers import router
from chats.apps.api.v1.internal.ai_features.views import FeaturePromptsView
from chats.apps.api.v1.internal.agents.views import AgentDisconnectView


urlpatterns = [
    path("rooms/report/", RoomsReportViewSet.as_view(), name="rooms_report"),
    path(
        "internal/ai_features/prompts/",
        FeaturePromptsView.as_view(),
        name="ai_features_prompts",
    ),
    path("model-fields/", ModelFieldsViewSet.as_view(), name="model-fields"),
    path("chats/report/", ReportFieldsValidatorViewSet.as_view(), name="chats-report"),
    path(
        "chats/agent/disconnect/",
        AgentDisconnectView.as_view(),
        name="agent_disconnect",
    ),
    path("", include(router.urls)),
]
