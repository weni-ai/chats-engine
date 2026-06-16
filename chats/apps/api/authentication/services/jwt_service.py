from typing import Optional, Union
from uuid import UUID

import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings

from chats.apps.api.authentication.exceptions import InvalidTokenError


class JWTService:
    """
    Service to generate JWT tokens for the project
    """

    def generate_jwt_token(
        self,
        project_uuid: Optional[Union[str, UUID]] = None,
        key: Optional[str] = None,
        vtex_account: Optional[str] = None,
    ) -> str:
        if key is None:
            key = settings.JWT_SECRET_KEY
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }

        if vtex_account is not None:
            payload["vtex_account"] = vtex_account

        if project_uuid is not None:
            payload["project_uuid"] = str(project_uuid)

        if not key:
            key = settings.JWT_SECRET_KEY

        token = jwt.encode(payload, key, algorithm="RS256")

        return token

    def decode_jwt_token(self, token: str, key: Optional[str] = None) -> dict:
        if key is None:
            key = settings.JWT_PUBLIC_KEY
        try:
            return jwt.decode(token, key, algorithms=["RS256"])
        except Exception as e:
            raise InvalidTokenError("Error decoding token") from e
