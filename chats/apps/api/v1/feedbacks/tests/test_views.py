from unittest.mock import patch
import uuid

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response


from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.projects.tests.decorators import with_project_permission


class BaseFeedbackViewSetTestCase(APITestCase):
    """
    Base test case for feedback views.
    """

    def get_should_show_feedback_form(self) -> Response:
        """
        Get the URL for the should show feedback form endpoint.
        """
        url = reverse("feedbacks-list")

        return self.client.get(url)

    def create_feedback(self, data: dict) -> Response:
        """
        Get the URL for the create feedback endpoint.
        """
        url = reverse("feedbacks-list")

        return self.client.post(url, data=data, format="json")


class TestFeedbackViewSetAsAnonymousUser(BaseFeedbackViewSetTestCase):
    """
    Test feedback view set as anonymous.
    """

    def test_cannot_get_should_show_feedback_form_as_anonymous(self) -> None:
        """
        Test that the feedback form should not be shown to anonymous users.
        """
        response = self.get_should_show_feedback_form()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_create_feedback_as_anonymous(self) -> None:
        """
        Test that the feedback form should not be shown to anonymous users.
        """
        response = self.create_feedback(
            data={
                "project_uuid": uuid.uuid4(),
                "rating": 5,
                "comment": "Test comment",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestFeedbackViewSetAsAuthenticatedUser(BaseFeedbackViewSetTestCase):
    """
    Test feedback view set as authenticated user.
    """

    def setUp(self) -> None:
        """
        Set up the test case.
        """
        self.user = User.objects.create_user(
            email="testuser@test.com",
        )
        self.project = Project.objects.create(name="Test Project")

        self.client.force_authenticate(user=self.user)

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.should_show_feedback_form",
    )
    def test_should_show_feedback_form_when_true(
        self, mock_should_show_feedback_form
    ) -> None:
        """
        Test that the feedback form should be shown to authenticated users.
        """
        mock_should_show_feedback_form.return_value = True
        response = self.get_should_show_feedback_form()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("should_show_feedback_form", response.data)
        self.assertTrue(response.data["should_show_feedback_form"])
        mock_should_show_feedback_form.assert_called_once_with(self.user)

    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.should_show_feedback_form",
    )
    def test_should_show_feedback_form_when_false(
        self, mock_should_show_feedback_form
    ) -> None:
        """
        Test that the feedback form should be shown to authenticated users.
        """
        mock_should_show_feedback_form.return_value = False
        response = self.get_should_show_feedback_form()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("should_show_feedback_form", response.data)
        self.assertFalse(response.data["should_show_feedback_form"])
        mock_should_show_feedback_form.assert_called_once_with(self.user)

    def test_cannot_create_feedback_without_project_uuid(self) -> None:
        """
        Test that the feedback form should not be shown to authenticated users.
        """
        response = self.create_feedback(data={"rating": 5, "comment": "Test comment"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["project_uuid"][0].code, "required")

    def test_cannot_create_feedback_without_permission(self) -> None:
        """
        Test that the feedback form should not be shown to authenticated users.
        """
        response = self.create_feedback(
            data={
                "project_uuid": self.project.uuid,
                "rating": 5,
                "comment": "Test comment",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission
    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.create_feedback",
    )
    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.can_create_feedback",
    )
    def test_cannot_create_feedback_with_project_permission_when_can_create_feedback_is_false(
        self, mock_can_create_feedback, mock_create_feedback
    ) -> None:
        """
        Test that the feedback form should be shown to authenticated users.
        """
        mock_can_create_feedback.return_value = False
        response = self.create_feedback(
            data={
                "project_uuid": self.project.uuid,
                "rating": 5,
                "comment": "Test comment",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_can_create_feedback.assert_called_once_with(self.user)
        mock_create_feedback.assert_not_called()

    @with_project_permission
    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.create_feedback",
    )
    @patch(
        "chats.apps.feedbacks.services.UserFeedbackService.can_create_feedback",
    )
    def test_can_create_feedback_with_project_permission_when_can_create_feedback_is_true(
        self, mock_can_create_feedback, mock_create_feedback
    ) -> None:
        """
        Test that the feedback form should be shown to authenticated users.
        """
        mock_can_create_feedback.return_value = True
        response = self.create_feedback(
            data={
                "project_uuid": self.project.uuid,
                "rating": 5,
                "comment": "Test comment",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_can_create_feedback.assert_called_once_with(self.user)
        mock_create_feedback.assert_called_once_with(
            self.user, self.project.uuid, 5, "Test comment"
        )
