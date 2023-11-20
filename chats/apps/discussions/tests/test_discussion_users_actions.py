from django.urls import reverse
from parameterized import parameterized
from rest_framework import status
from rest_framework.test import APITestCase


class CreateDiscussionUserViewActionTests(APITestCase):
    # ("Scenario description", room, queue, subject, initial_message, user_token, expected_response_status)
    fixtures = [
        "chats/fixtures/fixture_app.json",
        "chats/fixtures/fixture_discussion.json",
    ]

    parameters = [
        # Success parameters
        (
            "Creator can add users to discussion",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            "agentqueue@chats.weni.ai",
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            status.HTTP_201_CREATED,
        ),
        (
            "Queue user can add itself to the discussion",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            "foobar@chats.weni.ai",
            "a0358e20c8755568189d3a7e688ac3ec771317e2",
            status.HTTP_201_CREATED,
        ),
        (
            "Admin can add itself to the discussion",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            "agentqueue@chats.weni.ai",
            "4215e6d6666e54f7db9f98100533aa68909fd855",
            status.HTTP_201_CREATED,
        ),
        (
            "Queue user cannot add other users to the discussion",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            "agentqueue@chats.weni.ai",
            "a0358e20c8755568189d3a7e688ac3ec771317e2",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            "Added users cannot add other users to the discussion",
            "36584c70-aaf9-4f5c-b0c3-0547bb23879d",
            "internal@weni.ai",
            "a0358e20c8755568189d3a7e688ac3ec771317e2",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            "Cannot add a user that is already added to the discussion",
            "36584c70-aaf9-4f5c-b0c3-0547bb23879d",
            "foobar@chats.weni.ai",
            "a0358e20c8755568189d3a7e688ac3ec771317e2",
            status.HTTP_400_BAD_REQUEST,
        ),
    ]

    def _create_discussion_user(self, token, discussion, body):
        url = reverse("discussion-detail", kwargs={"uuid": discussion}) + "add_agents/"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.post(url, format="json", data=body)
        return response

    @parameterized.expand(parameters)
    def test_add_user_to_discussion(
        self, _, discussion, user_email, token, expected_status
    ):
        discussion_data = {
            "user_email": user_email,
        }

        response = self._create_discussion_user(token, discussion, discussion_data)
        self.assertEqual(response.status_code, expected_status)


class ListDiscussionUserViewActionTests(APITestCase):
    fixtures = [
        "chats/fixtures/fixture_app.json",
        "chats/fixtures/fixture_discussion.json",
    ]
    parameters = [
        (
            "Creator can list all users on the discussions",
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            status.HTTP_200_OK,
            1,
        ),
        (
            "Admin can list all users on the discussions",
            "4215e6d6666e54f7db9f98100533aa68909fd855",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            status.HTTP_200_OK,
            1,
        ),
        (
            "Added user can list all users on the discussions",
            "a0358e20c8755568189d3a7e688ac3ec771317e2",
            "36584c70-aaf9-4f5c-b0c3-0547bb23879d",
            status.HTTP_200_OK,
            3,
        ),
        (
            "Outside project user cannot list discussion users",
            "1218da72b087b8be7f0e2520a515e968ab866fdd",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            status.HTTP_403_FORBIDDEN,
            None,
        ),
    ]

    def _list_discussion_user(self, token, discussion, params={}):
        url = reverse("discussion-detail", kwargs={"uuid": discussion}) + "list_agents/"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data=params)
        return response

    @parameterized.expand(parameters)
    def test_discussion_user_list(
        self, _, token, discussion, expected_status, expected_count
    ):
        response = self._list_discussion_user(token=token, discussion=discussion)
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response.json().get("count"), expected_count)
