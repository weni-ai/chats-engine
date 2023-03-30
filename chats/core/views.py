import logging
import re
import requests
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()
LOGGER = logging.getLogger(__name__)


def get_auth_token() -> str:
    request = requests.post(
        url=settings.OIDC_OP_TOKEN_ENDPOINT,
        data={
            "client_id": settings.OIDC_ADMIN_CLIENT_ID,
            "client_secret": settings.OIDC_ADMIN_CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
    )
    token = request.json().get("access_token")
    return f"Bearer {token}"


def get_internal_headers() -> dict:
    return {
        "Content-Type": "application/json; charset: utf-8",
        "Authorization": get_auth_token(),
    }


def persist_keycloak_user_by_email(user_email: str):  # TODO: ERROR HANDLING
    url = settings.OIDC_OP_USERS_DATA_ENDPOINT + f"?email={user_email}"
    headers = get_internal_headers()
    response = requests.get(url, headers=headers)
    data = response.json()
    try:
        user_data = data[0]
    except (IndexError, KeyError):
        error_str = f"[{response.status_code}] Error while searching the user {user_email} on keycloak"
        LOGGER.debug(error_str)

        return
    email = user_data.get("email")
    user = User.objects.get_or_create(email=email)[0]
    first_name = user_data.get("firstName", "") or user_data.get("username", "")
    user.first_name = first_name[:29]  # TODO: Maybe change this limit in the models
    user.last_name = user_data.get("lastName", "")
    user.save()
