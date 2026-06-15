from django.urls import path
from chats.apps.api.authentication.tests.test_classes import (
    InternalAPITokenAuthenticationView,
    GenericJWTAuthenticationView,
)

urlpatterns = [
    path(
        "jwt-authentication/",
        GenericJWTAuthenticationView.as_view(),
        name="jwt-authentication-view",
    ),
    path(
        "internal-api-token-authentication/",
        InternalAPITokenAuthenticationView.as_view(),
        name="internal-api-token-authentication-view",
    ),
]
