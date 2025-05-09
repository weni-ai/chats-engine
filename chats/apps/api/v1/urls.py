from django.urls import include, path

from chats.apps.api.v1.routers import router
from chats.apps.api.v1.internal.ai_features.views import FeaturePromptsView

urlpatterns = [
    path(
        "internal/ai_features/prompts/",
        FeaturePromptsView.as_view(),
        name="ai_features_prompts",
    ),
    path("", include(router.urls)),
]
