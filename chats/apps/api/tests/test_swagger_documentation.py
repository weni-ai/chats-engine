"""
Unit tests for Swagger documentation features.
These tests validate that the swagger_tag attribute and TaggedSwaggerAutoSchema
work correctly without breaking the API functionality.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from chats.apps.api.swagger import TaggedSwaggerAutoSchema


class TaggedSwaggerAutoSchemaTests(TestCase):
    """Test suite for the TaggedSwaggerAutoSchema class."""

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_get_tags_returns_list_when_swagger_tag_is_string(self):
        """Test that get_tags returns a list when swagger_tag is a string."""
        schema = TaggedSwaggerAutoSchema(
            view=MagicMock(swagger_tag="Rooms"),
            path="/api/v1/rooms/",
            method="get",
            components=None,
            request=None,
            overrides={},
        )
        tags = schema.get_tags()
        self.assertEqual(tags, ["Rooms"])

    def test_get_tags_returns_list_when_swagger_tag_is_list(self):
        """Test that get_tags returns the list when swagger_tag is a list."""
        schema = TaggedSwaggerAutoSchema(
            view=MagicMock(swagger_tag=["Rooms", "Messages"]),
            path="/api/v1/rooms/",
            method="get",
            components=None,
            request=None,
            overrides={},
        )
        tags = schema.get_tags()
        self.assertEqual(tags, ["Rooms", "Messages"])

    def test_get_tags_returns_list_when_swagger_tag_is_tuple(self):
        """Test that get_tags returns a list when swagger_tag is a tuple."""
        schema = TaggedSwaggerAutoSchema(
            view=MagicMock(swagger_tag=("Rooms", "Messages")),
            path="/api/v1/rooms/",
            method="get",
            components=None,
            request=None,
            overrides={},
        )
        tags = schema.get_tags()
        self.assertEqual(tags, ["Rooms", "Messages"])

    def test_get_tags_calls_parent_when_no_swagger_tag(self):
        """Test that get_tags calls parent method when no swagger_tag is set."""
        schema = TaggedSwaggerAutoSchema(
            view=MagicMock(spec=[]),
            path="/api/v1/rooms/",
            method="get",
            components=None,
            request=None,
            overrides={},
        )
        with patch.object(
            TaggedSwaggerAutoSchema.__bases__[0],
            "get_tags",
            return_value=["default"],
        ):
            tags = schema.get_tags()
            self.assertIsInstance(tags, list)

    def test_get_summary_with_dict_swagger_summary(self):
        """Test that get_summary_and_description works with dict swagger_summary."""
        view_mock = MagicMock()
        view_mock.swagger_summary = {"get": "List all rooms", "post": "Create a room"}
        view_mock.swagger_description = None

        schema = TaggedSwaggerAutoSchema(
            view=view_mock,
            path="/api/v1/rooms/",
            method="get",
            components=None,
            request=None,
            overrides={},
        )

        with patch.object(
            TaggedSwaggerAutoSchema.__bases__[0],
            "get_summary_and_description",
            return_value=("", ""),
        ):
            summary, description = schema.get_summary_and_description()
            self.assertEqual(summary, "List all rooms")

    def test_get_summary_with_string_swagger_summary(self):
        """Test that get_summary_and_description works with string swagger_summary."""
        view_mock = MagicMock()
        view_mock.swagger_summary = "List all rooms"
        view_mock.swagger_description = None

        schema = TaggedSwaggerAutoSchema(
            view=view_mock,
            path="/api/v1/rooms/",
            method="get",
            components=None,
            request=None,
            overrides={},
        )

        with patch.object(
            TaggedSwaggerAutoSchema.__bases__[0],
            "get_summary_and_description",
            return_value=("", ""),
        ):
            summary, description = schema.get_summary_and_description()
            self.assertEqual(summary, "List all rooms")


class SwaggerTagAttributeTests(TestCase):
    """Test that all viewsets have the swagger_tag attribute properly set."""

    def test_rooms_viewset_has_swagger_tag(self):
        """Test that RoomViewset has swagger_tag."""
        from chats.apps.api.v1.rooms.viewsets import RoomViewset

        self.assertTrue(hasattr(RoomViewset, "swagger_tag"))
        self.assertEqual(RoomViewset.swagger_tag, "Rooms")

    def test_messages_viewset_has_swagger_tag(self):
        """Test that MessageViewset has swagger_tag."""
        from chats.apps.api.v1.msgs.viewsets import MessageViewset

        self.assertTrue(hasattr(MessageViewset, "swagger_tag"))
        self.assertEqual(MessageViewset.swagger_tag, "Messages")

    def test_projects_viewset_has_swagger_tag(self):
        """Test that ProjectViewset has swagger_tag."""
        from chats.apps.api.v1.projects.viewsets import ProjectViewset

        self.assertTrue(hasattr(ProjectViewset, "swagger_tag"))
        self.assertEqual(ProjectViewset.swagger_tag, "Projects")

    def test_sectors_viewset_has_swagger_tag(self):
        """Test that SectorViewset has swagger_tag."""
        from chats.apps.api.v1.sectors.viewsets import SectorViewset

        self.assertTrue(hasattr(SectorViewset, "swagger_tag"))
        self.assertEqual(SectorViewset.swagger_tag, "Sectors")

    def test_queues_viewset_has_swagger_tag(self):
        """Test that QueueViewset has swagger_tag."""
        from chats.apps.api.v1.queues.viewsets import QueueViewset

        self.assertTrue(hasattr(QueueViewset, "swagger_tag"))
        self.assertEqual(QueueViewset.swagger_tag, "Queues")

    def test_dashboard_viewset_has_swagger_tag(self):
        """Test that DashboardLiveViewset has swagger_tag."""
        from chats.apps.api.v1.dashboard.viewsets import DashboardLiveViewset

        self.assertTrue(hasattr(DashboardLiveViewset, "swagger_tag"))
        self.assertEqual(DashboardLiveViewset.swagger_tag, "Dashboard")

    def test_contacts_viewset_has_swagger_tag(self):
        """Test that ContactViewset has swagger_tag."""
        from chats.apps.api.v1.contacts.viewsets import ContactViewset

        self.assertTrue(hasattr(ContactViewset, "swagger_tag"))
        self.assertEqual(ContactViewset.swagger_tag, "Contacts")

    def test_login_viewset_has_swagger_tag(self):
        """Test that LoginViewset has swagger_tag."""
        from chats.apps.api.v1.accounts.viewsets import LoginViewset

        self.assertTrue(hasattr(LoginViewset, "swagger_tag"))
        self.assertEqual(LoginViewset.swagger_tag, "Authentication")

    def test_quick_messages_viewset_has_swagger_tag(self):
        """Test that QuickMessageViewset has swagger_tag."""
        from chats.apps.api.v1.quickmessages.viewsets import QuickMessageViewset

        self.assertTrue(hasattr(QuickMessageViewset, "swagger_tag"))
        self.assertEqual(QuickMessageViewset.swagger_tag, "Quick Messages")

    def test_discussions_viewset_has_swagger_tag(self):
        """Test that DiscussionViewSet has swagger_tag."""
        from chats.apps.discussions.views.discussion import DiscussionViewSet

        self.assertTrue(hasattr(DiscussionViewSet, "swagger_tag"))
        self.assertEqual(DiscussionViewSet.swagger_tag, "Discussions")

    def test_history_viewset_has_swagger_tag(self):
        """Test that HistoryRoomViewset has swagger_tag."""
        from chats.apps.history.views.history_rooms import HistoryRoomViewset

        self.assertTrue(hasattr(HistoryRoomViewset, "swagger_tag"))
        self.assertEqual(HistoryRoomViewset.swagger_tag, "History")

    def test_external_rooms_viewset_has_swagger_tag(self):
        """Test that RoomFlowViewSet has swagger_tag."""
        from chats.apps.api.v1.external.rooms.viewsets import RoomFlowViewSet

        self.assertTrue(hasattr(RoomFlowViewSet, "swagger_tag"))
        self.assertEqual(RoomFlowViewSet.swagger_tag, "Integrations")

    def test_feature_flags_viewset_has_swagger_tag(self):
        """Test that FeatureFlagsViewSet has swagger_tag."""
        from chats.apps.api.v1.feature_flags.views import FeatureFlagsViewSet

        self.assertTrue(hasattr(FeatureFlagsViewSet, "swagger_tag"))
        self.assertEqual(FeatureFlagsViewSet.swagger_tag, "Feature Flags")

    def test_feedback_viewset_has_swagger_tag(self):
        """Test that FeedbackViewSet has swagger_tag."""
        from chats.apps.api.v1.feedbacks.views import FeedbackViewSet

        self.assertTrue(hasattr(FeedbackViewSet, "swagger_tag"))
        self.assertEqual(FeedbackViewSet.swagger_tag, "Feedback")

    def test_organizations_viewset_has_swagger_tag(self):
        """Test that OrgProjectViewSet has swagger_tag."""
        from chats.apps.api.v1.orgs.viewsets import OrgProjectViewSet

        self.assertTrue(hasattr(OrgProjectViewSet, "swagger_tag"))
        self.assertEqual(OrgProjectViewSet.swagger_tag, "Organizations")

    def test_group_sectors_viewset_has_swagger_tag(self):
        """Test that GroupSectorViewset has swagger_tag."""
        from chats.apps.api.v1.groups_sectors.viewsets import GroupSectorViewset

        self.assertTrue(hasattr(GroupSectorViewset, "swagger_tag"))
        self.assertEqual(GroupSectorViewset.swagger_tag, "Groups")

    def test_custom_status_viewset_has_swagger_tag(self):
        """Test that CustomStatusTypeViewSet has swagger_tag."""
        from chats.apps.api.v1.projects.viewsets import CustomStatusTypeViewSet

        self.assertTrue(hasattr(CustomStatusTypeViewSet, "swagger_tag"))
        self.assertEqual(CustomStatusTypeViewSet.swagger_tag, "Custom Status")

    def test_agents_view_has_swagger_tag(self):
        """Test that AgentDisconnectView has swagger_tag."""
        from chats.apps.api.v1.internal.agents.views import AgentDisconnectView

        self.assertTrue(hasattr(AgentDisconnectView, "swagger_tag"))
        self.assertEqual(AgentDisconnectView.swagger_tag, "Agents")

    def test_ai_features_view_has_swagger_tag(self):
        """Test that FeaturePromptsView has swagger_tag."""
        from chats.apps.api.v1.internal.ai_features.views import FeaturePromptsView

        self.assertTrue(hasattr(FeaturePromptsView, "swagger_tag"))
        self.assertEqual(FeaturePromptsView.swagger_tag, "AI Features")


class ViewsetDocstringTests(TestCase):
    """Test that viewsets have proper docstrings after swagger_tag."""

    def test_rooms_report_viewset_has_docstring(self):
        """Test that RoomsReportViewSet has a proper docstring."""
        from chats.apps.api.v1.rooms.viewsets import RoomsReportViewSet

        self.assertIsNotNone(RoomsReportViewSet.__doc__)
        self.assertIn("report", RoomsReportViewSet.__doc__.lower())

    def test_room_note_viewset_has_docstring(self):
        """Test that RoomNoteViewSet has a proper docstring."""
        from chats.apps.api.v1.rooms.viewsets import RoomNoteViewSet

        self.assertIsNotNone(RoomNoteViewSet.__doc__)
        self.assertIn("note", RoomNoteViewSet.__doc__.lower())

    def test_feedback_viewset_has_docstring(self):
        """Test that FeedbackViewSet has a proper docstring."""
        from chats.apps.api.v1.feedbacks.views import FeedbackViewSet

        self.assertIsNotNone(FeedbackViewSet.__doc__)
        self.assertIn("feedback", FeedbackViewSet.__doc__.lower())

    def test_feature_flags_viewset_has_docstring(self):
        """Test that FeatureFlagsViewSet has a proper docstring."""
        from chats.apps.api.v1.feature_flags.views import FeatureFlagsViewSet

        self.assertIsNotNone(FeatureFlagsViewSet.__doc__)
        self.assertIn("feature", FeatureFlagsViewSet.__doc__.lower())

    def test_feature_prompts_view_has_docstring(self):
        """Test that FeaturePromptsView has a proper docstring."""
        from chats.apps.api.v1.internal.ai_features.views import FeaturePromptsView

        self.assertIsNotNone(FeaturePromptsView.__doc__)
        self.assertIn("prompt", FeaturePromptsView.__doc__.lower())


class SwaggerSettingsTests(TestCase):
    """Test that Swagger settings are properly configured."""

    def test_swagger_settings_has_custom_auto_schema_class(self):
        """Test that SWAGGER_SETTINGS has custom auto schema class."""
        from django.conf import settings

        self.assertIn("DEFAULT_AUTO_SCHEMA_CLASS", settings.SWAGGER_SETTINGS)
        self.assertEqual(
            settings.SWAGGER_SETTINGS["DEFAULT_AUTO_SCHEMA_CLASS"],
            "chats.apps.api.swagger.TaggedSwaggerAutoSchema",
        )

    def test_swagger_settings_has_tags_defined(self):
        """Test that SWAGGER_SETTINGS has tags defined."""
        from django.conf import settings

        self.assertIn("TAGS", settings.SWAGGER_SETTINGS)
        self.assertIsInstance(settings.SWAGGER_SETTINGS["TAGS"], list)
        self.assertGreater(len(settings.SWAGGER_SETTINGS["TAGS"]), 0)

    def test_swagger_tags_have_required_fields(self):
        """Test that each tag has name and description."""
        from django.conf import settings

        for tag in settings.SWAGGER_SETTINGS["TAGS"]:
            self.assertIn("name", tag)
            self.assertIn("description", tag)
            self.assertIsInstance(tag["name"], str)
            self.assertIsInstance(tag["description"], str)

    def test_swagger_settings_has_expected_tags(self):
        """Test that SWAGGER_SETTINGS has all expected tags."""
        from django.conf import settings

        expected_tags = [
            "Authentication",
            "Users",
            "Projects",
            "Rooms",
            "Queues",
            "Messages",
            "Dashboard",
            "Sectors",
            "Groups",
            "Contacts",
            "Quick Messages",
            "Integrations",
            "Custom Status",
            "Feature Flags",
            "Feedback",
            "Organizations",
            "AI Features",
            "Agents",
            "Discussions",
            "History",
        ]
        defined_tag_names = [tag["name"] for tag in settings.SWAGGER_SETTINGS["TAGS"]]

        for expected_tag in expected_tags:
            self.assertIn(
                expected_tag,
                defined_tag_names,
                f"Tag '{expected_tag}' not found in SWAGGER_SETTINGS",
            )
