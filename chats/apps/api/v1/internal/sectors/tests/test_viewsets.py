from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector


class SectorRequiredTagsEndpointTestCase(APITestCase):
    """Tests for the sector required_tags check endpoint."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email="test@test.com")
        self.project = Project.objects.create(name="Test Project")

        self.sector_with_required_tags = Sector.objects.create(
            name="Sector With Required Tags",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
            required_tags=True,
        )

        self.sector_without_required_tags = Sector.objects.create(
            name="Sector Without Required Tags",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
            required_tags=False,
        )

        self.client.force_authenticate(self.user)

    def test_check_required_tags_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        self.client.force_authenticate(user=None)
        url = reverse(
            "sector_internal-check-required-tags",
            kwargs={"uuid": self.sector_with_required_tags.uuid},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @with_internal_auth
    def test_check_required_tags_when_true(self):
        """Test endpoint returns True when sector has required_tags enabled."""
        url = reverse(
            "sector_internal-check-required-tags",
            kwargs={"uuid": self.sector_with_required_tags.uuid},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.sector_with_required_tags.uuid))
        self.assertTrue(response.data["required_tags"])

    @with_internal_auth
    def test_check_required_tags_when_false(self):
        """Test endpoint returns False when sector has required_tags disabled."""
        url = reverse(
            "sector_internal-check-required-tags",
            kwargs={"uuid": self.sector_without_required_tags.uuid},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["uuid"], str(self.sector_without_required_tags.uuid)
        )
        self.assertFalse(response.data["required_tags"])

    @with_internal_auth
    def test_check_required_tags_nonexistent_sector(self):
        """Test endpoint returns 404 for non-existent sector."""
        url = reverse(
            "sector_internal-check-required-tags",
            kwargs={"uuid": "00000000-0000-0000-0000-000000000000"},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @with_internal_auth
    def test_check_required_tags_response_structure(self):
        """Test that response contains expected fields."""
        url = reverse(
            "sector_internal-check-required-tags",
            kwargs={"uuid": self.sector_with_required_tags.uuid},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("uuid", response.data)
        self.assertIn("required_tags", response.data)
        self.assertEqual(len(response.data), 2)

    def test_check_required_tags_without_internal_permission(self):
        """Test that requests without internal permission are rejected."""
        url = reverse(
            "sector_internal-check-required-tags",
            kwargs={"uuid": self.sector_with_required_tags.uuid},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
