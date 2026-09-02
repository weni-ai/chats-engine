from unittest.mock import MagicMock

from django.test import SimpleTestCase

from chats.apps.assisted_sales.exceptions import CopilotConnectError
from chats.apps.assisted_sales.usecases import (
    CheckCopilotCreatePermissionUseCase,
    user_can_create_copilot,
)

AVAILABLE_ROLES = {
    "0": "not set",
    "1": "viewer",
    "2": "contributor",
    "3": "moderator",
    "4": "support",
    "5": "Chat user",
    "6": "marketing",
}


def _authorization(role):
    return {
        "user": "member@example.com",
        "project_authorization": role,
        "available_roles": AVAILABLE_ROLES,
    }


class UserCanCreateCopilotTests(SimpleTestCase):
    def test_moderator_can_create(self):
        self.assertTrue(user_can_create_copilot(_authorization(3)))

    def test_contributor_cannot_create(self):
        self.assertFalse(user_can_create_copilot(_authorization(2)))

    def test_viewer_cannot_create(self):
        self.assertFalse(user_can_create_copilot(_authorization(1)))

    def test_support_cannot_create(self):
        self.assertFalse(user_can_create_copilot(_authorization(4)))

    def test_missing_roles_cannot_create(self):
        self.assertFalse(user_can_create_copilot({"project_authorization": 3}))

    def test_invalid_authorization_cannot_create(self):
        self.assertFalse(
            user_can_create_copilot(
                {"project_authorization": "admin", "available_roles": AVAILABLE_ROLES}
            )
        )


class CheckCopilotCreatePermissionUseCaseTests(SimpleTestCase):
    def test_returns_true_when_connect_role_is_moderator(self):
        client = MagicMock()
        client.get_project_authorization.return_value = _authorization(3)

        can_create = CheckCopilotCreatePermissionUseCase(client=client).execute(
            project_uuid="project-uuid",
            user_email="member@example.com",
        )

        self.assertTrue(can_create)
        client.get_project_authorization.assert_called_once_with(
            "project-uuid", "member@example.com"
        )

    def test_returns_false_when_connect_role_is_not_moderator(self):
        client = MagicMock()
        client.get_project_authorization.return_value = _authorization(2)

        can_create = CheckCopilotCreatePermissionUseCase(client=client).execute(
            project_uuid="project-uuid",
            user_email="member@example.com",
        )

        self.assertFalse(can_create)

    def test_raises_when_connect_fails(self):
        client = MagicMock()
        client.get_project_authorization.side_effect = CopilotConnectError(
            status_code=502, error="Connect unavailable"
        )

        with self.assertRaises(CopilotConnectError):
            CheckCopilotCreatePermissionUseCase(client=client).execute(
                project_uuid="project-uuid",
                user_email="member@example.com",
            )
