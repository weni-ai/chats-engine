import pytest
from unittest import mock


@pytest.fixture(autouse=True)
def use_dummy_internal_api_token(settings):
    settings.INTERNAL_API_TOKEN = "dummy-token"


@pytest.fixture(autouse=True)
def use_mock_get_userinfo():
    with mock.patch(
        "chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend.get_userinfo",
        return_value={},
    ) as mock_get_userinfo:
        yield mock_get_userinfo
