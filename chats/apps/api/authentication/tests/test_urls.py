from django.urls import path
from chats.apps.api.authentication.tests.test_classes import (
    InternalAPITokenAuthenticationView,
    JWTAuthenticationView,
)

urlpatterns = [
    path(
        "jwt-authentication/",
        JWTAuthenticationView.as_view(),
        name="jwt-authentication-view",
    ),
    path(
        "internal-api-token-authentication/",
        InternalAPITokenAuthenticationView.as_view(),
        name="internal-api-token-authentication-view",
    ),
]
