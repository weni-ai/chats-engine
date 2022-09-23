import re
import requests
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


def get_auth_token() -> str:
    request = requests.post(
        url=settings.OIDC_OP_TOKEN_ENDPOINT,
        data={
            "client_id": settings.OIDC_RP_CLIENT_ID,
            "client_secret": settings.OIDC_RP_CLIENT_SECRET,
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
    if User.objects.filter(email=user_email).exists():
        return
    url = settings.OIDC_OP_USERS_DATA_ENDPOINT + f"?email={user_email}"
    headers = get_internal_headers()
    response = requests.get(url, headers=headers)
    user_data = response.json()[0]

    email = user_data.get("email")
    username = user_data.get("username")
    username = re.sub("[^A-Za-z0-9]+", "", username)
    user = User.objects.create_user(email, username)

    user.first_name = user_data.get("first_name", "")
    user.last_name = user_data.get("last_name", "")
    user.save()
