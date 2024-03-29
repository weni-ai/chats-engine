from django.urls import reverse
from parameterized import parameterized
from rest_framework import status
from rest_framework.test import APITestCase


class CreateDiscussionViewActionTests(APITestCase):
    # ("Scenario description", room, queue, subject, initial_message, user_token, expected_response_status)
    fixtures = [
        "chats/fixtures/fixture_app.json",
        "chats/fixtures/fixture_discussion.json",
    ]

    parameters = [
        # Success parameters
        (
            "Active room user create discussion to an authorized queue",
            "307dc034-2ecf-48b0-9d15-b4841ec7da5f",
            "f362336c-672b-4962-be82-efdf6101be6d",
            None,
            None,
            "59e5b85e2f0134c4ee9f72037e379c94390697ce",
            status.HTTP_201_CREATED,
        ),
        (
            "Active room user create discussion to an unauthorized queue",
            "307dc034-2ecf-48b0-9d15-b4841ec7da5f",
            "687ca2aa-978b-48e6-ae95-1d03fc1d1a5b",
            None,
            None,
            "59e5b85e2f0134c4ee9f72037e379c94390697ce",
            status.HTTP_201_CREATED,
        ),
        (
            "Discussion on unactive room can be openned by any project user",
            "47a983f3-d4b0-4fd4-a66c-f2f3856fb2ac",
            "f362336c-672b-4962-be82-efdf6101be6d",
            None,
            None,
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            status.HTTP_201_CREATED,
        ),
        (
            "Admin can create discussion in any room",
            "307dc034-2ecf-48b0-9d15-b4841ec7da5f",
            "687ca2aa-978b-48e6-ae95-1d03fc1d1a5b",
            None,
            None,
            "4215e6d6666e54f7db9f98100533aa68909fd855",
            status.HTTP_201_CREATED,
        ),
        (
            "Any manager can create discussion in any room",
            "307dc034-2ecf-48b0-9d15-b4841ec7da5f",
            "687ca2aa-978b-48e6-ae95-1d03fc1d1a5b",
            None,
            None,
            "c23e0173ac75c1a9ab448967e6a624e1a6ac1a2d",
            status.HTTP_201_CREATED,
        ),
        # Failure parameters
        (
            "Discussions cannot be openned in inexistent rooms",
            "09d0f92e-ccd6-481b-8802-d4edf99281da",
            "f362336c-672b-4962-be82-efdf6101be6d",
            None,
            None,
            "59e5b85e2f0134c4ee9f72037e379c94390697ce",
            status.HTTP_403_FORBIDDEN,
        ),
        (
            "Different user than Active room user cannot create discussion",
            "307dc034-2ecf-48b0-9d15-b4841ec7da5f",
            "687ca2aa-978b-48e6-ae95-1d03fc1d1a5b",
            None,
            None,
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            status.HTTP_403_FORBIDDEN,
        ),
        (
            "Discussions cannot be openned when the room already have an active one",
            "50da4076-1f3b-4355-9a2e-be91bd6a410c",
            "f362336c-672b-4962-be82-efdf6101be6d",
            None,
            None,
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            status.HTTP_409_CONFLICT,
        ),
        (
            "discussion cannot be openned to another project",
            "307dc034-2ecf-48b0-9d15-b4841ec7da5f",
            "e17ca4d6-af57-4d12-8dd2-a25952c94400",
            None,
            None,
            "59e5b85e2f0134c4ee9f72037e379c94390697ce",
            status.HTTP_400_BAD_REQUEST,
        ),
    ]

    def _create_discussion(self, token, body=None):
        url = reverse("discussion-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.post(url, format="json", data=body)
        return response

    @parameterized.expand(parameters)
    def test_open_discussion(
        self, _, room, queue, subject, initial_message, token, expected_status
    ):
        discussion_data = {
            "room": room,
            "queue": queue,
            "subject": subject or "A very reasonable subject for opening a discussion",
            "initial_message": initial_message
            or """A very long and large text that has no character limits,
            so we'll write as much as we want....~""",
        }

        response = self._create_discussion(token=token, body=discussion_data)
        self.assertEqual(response.status_code, expected_status)


class ListDiscussionsViewActionTests(APITestCase):
    fixtures = [
        "chats/fixtures/fixture_app.json",
        "chats/fixtures/fixture_discussion.json",
    ]
    parameters = [
        (
            "Agent with no access to discussion will not receive any",
            "dae39bcc-bdc2-4b03-b4da-023a117f8474",
            True,
            "59e5b85e2f0134c4ee9f72037e379c94390697ce",
            status.HTTP_200_OK,
            0,
        ),
        (
            "Agent can only retrieve their discussions or queued discussions when they have access to the queue",
            "dae39bcc-bdc2-4b03-b4da-023a117f8474",
            True,
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            status.HTTP_200_OK,
            2,
        ),
        (
            "Agent cannot retrieve discussions from other projects they have permission on",
            "34a93b52-231e-11ed-861d-0242ac120002",
            True,
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            status.HTTP_200_OK,
            0,
        ),
        (
            "Admin can list all active discussions on the project",
            "dae39bcc-bdc2-4b03-b4da-023a117f8474",
            True,
            "4215e6d6666e54f7db9f98100533aa68909fd855",
            status.HTTP_200_OK,
            2,
        ),
        (
            "Agent List not active discussions",
            "dae39bcc-bdc2-4b03-b4da-023a117f8474",
            False,
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            status.HTTP_200_OK,
            1,
        ),
    ]

    def _list_discussions(self, token, params=None):
        url = reverse("discussion-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data=params)
        return response

    @parameterized.expand(parameters)
    def test_list_discussions(
        self, _, project, is_active, token, expected_status, expected_count
    ):
        query_filters = {"project": project, "is_active": is_active}
        response = self._list_discussions(token=token, params=query_filters)
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response.data.get("count"), expected_count)


class DestroyDiscussionsViewActionTests(APITestCase):
    fixtures = [
        "chats/fixtures/fixture_app.json",
        "chats/fixtures/fixture_discussion.json",
    ]
    parameters = [
        (
            "Creator can close discussions",
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            status.HTTP_204_NO_CONTENT,
        ),
        (
            "Admin can close discussions",
            "4215e6d6666e54f7db9f98100533aa68909fd855",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            status.HTTP_204_NO_CONTENT,
        ),
        (
            "Added user cannot close discussions",
            "59e5b85e2f0134c4ee9f72037e379c94390697ce",
            "36584c70-aaf9-4f5c-b0c3-0547bb23879d",
            status.HTTP_403_FORBIDDEN,
        ),
    ]

    def _destroy_discussion(self, token, discussion):
        url = reverse("discussion-detail", kwargs={"uuid": discussion})

        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.delete(url)
        return response

    @parameterized.expand(parameters)
    def test_destroy_discussions(self, _, token, discussion, expected_status):
        response = self._destroy_discussion(token=token, discussion=discussion)
        self.assertEqual(response.status_code, expected_status)


class DetailDiscussionsViewActionTests(APITestCase):
    fixtures = [
        "chats/fixtures/fixture_app.json",
        "chats/fixtures/fixture_discussion.json",
    ]
    parameters = [
        (
            "Creator can detail discussions",
            "d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            status.HTTP_200_OK,
        ),
        (
            "Admin can detail discussions",
            "4215e6d6666e54f7db9f98100533aa68909fd855",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            status.HTTP_200_OK,
        ),
        (
            "Added user can detail discussions",
            "59e5b85e2f0134c4ee9f72037e379c94390697ce",
            "36584c70-aaf9-4f5c-b0c3-0547bb23879d",
            status.HTTP_200_OK,
        ),
        (
            "Non permitted users cannot detail discussions",
            "59e5b85e2f0134c4ee9f72037e379c94390697ce",
            "3c2d1694-8db9-4f09-976b-e263f9d79c99",
            status.HTTP_403_FORBIDDEN,
        ),
    ]

    def _detail_discussion(self, token, discussion):
        url = reverse("discussion-detail", kwargs={"uuid": discussion})

        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url)
        return response

    @parameterized.expand(parameters)
    def test_detail_discussions(self, _, token, discussion, expected_status):
        response = self._detail_discussion(token=token, discussion=discussion)
        self.assertEqual(response.status_code, expected_status)
