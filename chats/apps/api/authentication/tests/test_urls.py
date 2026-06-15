from django.urls import path
from chats.apps.api.authentication.tests.test_classes import (
    InternalAPITokenAuthenticationView,
    GenericJWTAuthenticationView,
)
from chats.apps.api.authentication.tests.test_jwt_authentication import (
    MockJWTAuthenticationView,
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
    path(
        "mock-jwt-authentication/",
        MockJWTAuthenticationView.as_view(),
        name="mock-jwt-authentication-view",
    ),
]
