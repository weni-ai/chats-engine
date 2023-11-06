from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import DiscussionMessage

"""

[X]Success when creating with all the discussion fields.
[X]Success for anyone(in the project) who tries to open a discussion from a inactive room on the history.
[X]Success when creating a discussion with a different queue than the room.
[X]success on creating the initial_message when creating the discussion.


"""


class DiscussionCreationTests(APITestCase):
    fixtures = [
        "chats/fixtures/fixture_app.json",
        "chats/fixtures/fixture_discussion.json",
    ]

    def _create_discussion(self, token, params=None, body=None):
        url = reverse("discussion-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.post(url, format="json", json=body)
        return response

    def test_success_open_discussion_on_active_room(self):
        open_room_pk = "4857b3f7-90e0-4df6-a4b1-8f2f6f6b471a"
        queue = "f2519480-7e58-4fc4-9894-9ab1769e29cf"
        room_agent_token = "4215e6d6666e54f7db9f98100533aa68909fd855"

        discussion_data = {
            "room": open_room_pk,
            "queue": queue,
            "subject": "A very reasonable subject for opening a discussion",
            "initial_message": """A very long and large text that has no character limits,
             so we'll write as much as we want....~""",
        }

        response = self._create_discussion(token=room_agent_token, body=discussion_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        initial_msg = DiscussionMessage.objects.get(discussion=response.json()["uuid"])
        self.assertEqual(initial_msg.text, discussion_data["initial_message"])

    def test_success_admin_open_discussion_on_active_room(self):
        open_room_pk = "4857b3f7-90e0-4df6-a4b1-8f2f6f6b471a"
        queue = "f2519480-7e58-4fc4-9894-9ab1769e29cf"
        project_admin_token = "d116bca8757372f3b5936096473929ed1465915e"

        discussion_data = {
            "room": open_room_pk,
            "queue": queue,
            "subject": "A very reasonable subject for opening a discussion",
            "initial_message": """A very long and large text that has no character limits,
             so we'll write as much as we want....~""",
        }

        response = self._create_discussion(
            token=project_admin_token, body=discussion_data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_success_open_discussion_on_closed_room(self):
        closed_room_pk = "8eeace79-fbca-454f-a811-56116c87adc5"
        queue = "f341417b-5143-4469-a99d-f141a0676bd4"
        room_agent_token = "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa"

        discussion_data = {
            "room": closed_room_pk,
            "queue": queue,
            "subject": "A very reasonable subject for opening a discussion",
            "initial_message": """A very long and large text that has no character limits,
             so we'll write as much as we want....~""",
        }

        response = self._create_discussion(token=room_agent_token, body=discussion_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_success_open_discussion_on_different_queue(self):
        open_room_pk = "4857b3f7-90e0-4df6-a4b1-8f2f6f6b471a"
        queue = "f2519480-7e58-4fc4-9894-9ab1769e29cf"
        room_agent_token = "4215e6d6666e54f7db9f98100533aa68909fd855"

        discussion_data = {
            "room": open_room_pk,
            "queue": queue,
            "subject": "A very reasonable subject for opening a discussion",
            "initial_message": """A very long and large text that has no character limits,
             so we'll write as much as we want....~""",
        }

        response = self._create_discussion(token=room_agent_token, body=discussion_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_fail_open_on_active_discussion_room(self):
        open_room_pk = "4857b3f7-90e0-4df6-a4b1-8f2f6f6b471a"
        queue = "f2519480-7e58-4fc4-9894-9ab1769e29cf"
        room_agent_token = "4215e6d6666e54f7db9f98100533aa68909fd855"

        discussion_data = {
            "room": open_room_pk,
            "queue": queue,
            "subject": "A very reasonable subject for opening a discussion",
            "initial_message": """A very long and large text that has no character limits,
             so we'll write as much as we want....~""",
        }

        self._create_discussion(token=room_agent_token, body=discussion_data)
        response = self._create_discussion(token=room_agent_token, body=discussion_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fail_open_on_inexistent_room(self):
        open_room_pk = "09d0f92e-ccd6-481b-8802-d4edf99281da"
        queue = "f2519480-7e58-4fc4-9894-9ab1769e29cf"
        room_agent_token = "4215e6d6666e54f7db9f98100533aa68909fd855"

        discussion_data = {
            "room": open_room_pk,
            "queue": queue,
            "subject": "A very reasonable subject for opening a discussion",
            "initial_message": """A very long and large text that has no character limits,
             so we'll write as much as we want....~""",
        }

        response = self._create_discussion(token=room_agent_token, body=discussion_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fail_open_without_permission(self):
        open_room_pk = "4857b3f7-90e0-4df6-a4b1-8f2f6f6b471a"
        queue = "f2519480-7e58-4fc4-9894-9ab1769e29cf"
        not_in_project_user_token = "6e52f41093468740d96649736e66e3eb7fbd008a"

        discussion_data = {
            "room": open_room_pk,
            "queue": queue,
            "subject": "A very reasonable subject for opening a discussion",
            "initial_message": """A very long and large text that has no character limits,
             so we'll write as much as we want....~""",
        }

        response = self._create_discussion(
            token=not_in_project_user_token, body=discussion_data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fail_open_on_without_obrigatory_field(self):
        open_room_pk = "4857b3f7-90e0-4df6-a4b1-8f2f6f6b471a"
        queue = "f2519480-7e58-4fc4-9894-9ab1769e29cf"
        room_agent_token = "4215e6d6666e54f7db9f98100533aa68909fd855"

        discussion_data = {
            "room": open_room_pk,
            "queue": queue,
            "subject": "A very reasonable subject for opening a discussion",
        }

        response = self._create_discussion(token=room_agent_token, body=discussion_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fail_open_discussion_on_active_room_of_other_agent(self):
        closed_room_pk = "8eeace79-fbca-454f-a811-56116c87adc5"
        queue = "f341417b-5143-4469-a99d-f141a0676bd4"
        other_agent_token = "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa"

        discussion_data = {
            "room": closed_room_pk,
            "queue": queue,
            "subject": "A very reasonable subject for opening a discussion",
            "initial_message": """A very long and large text that has no character limits,
             so we'll write as much as we want....~""",
        }

        response = self._create_discussion(
            token=other_agent_token, body=discussion_data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
