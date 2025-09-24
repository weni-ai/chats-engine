from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.projects.serializers import ProjectInternalSerializer
from chats.apps.projects.models import ProjectPermission


class ProjectInternalSerializerTemplateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="admin@acme.com")

    @patch(
        "chats.apps.api.v1.internal.projects.serializers.get_user_id_by_email_cached",
        return_value=1,
    )
    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.api.v1.internal.projects.serializers.FlowRESTClient")
    def test_create_template_creates_permission_with_user_id(self, mock_flows, _cache):
        c = Mock()
        resp_sector = Mock(status_code=200)
        resp_sector.json.return_value = {"uuid": "sec-1"}
        resp_queue = Mock(status_code=200)
        c.create_ticketer.return_value = resp_sector
        c.create_queue.return_value = resp_queue
        mock_flows.return_value = c

        serializer = ProjectInternalSerializer(
            data={
                "name": "P",
                "timezone": "UTC",
                "is_template": True,
                "user_email": "Admin@Acme.com",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        perm = ProjectPermission.objects.get(project=instance, user_id="admin@acme.com")
        self.assertEqual(perm.role, 1)
