import uuid

from unittest.mock import Mock

from django.test import TestCase

from chats.apps.projects.models import Project
from chats.apps.projects.usecases.flows_templates import FlowsTemplatesUseCase


class TestFlowsTemplatesUseCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Test Project",
        )
        self.use_case = FlowsTemplatesUseCase(project_uuid=str(self.project.uuid))
        self.mock_flows_client = Mock()
        self.use_case.flows_client = self.mock_flows_client

        self.template_uuid = str(uuid.uuid4())
        self.template_name = "Example"
        self.template_data = {
            "uuid": self.template_uuid,
            "name": self.template_name,
            "category": "MARKETING",
        }

    def test_found_on_first_page(self):
        self.mock_flows_client.get_templates.return_value = {
            "next": None,
            "previous": None,
            "results": [self.template_data],
        }

        result = self.use_case.execute(name=self.template_name, uuid=self.template_uuid)

        self.assertEqual(result, self.template_data)
        self.mock_flows_client.get_templates.assert_called_once()

    def test_found_on_second_page(self):
        other_template = {
            "uuid": str(uuid.uuid4()),
            "name": "Other",
        }
        self.mock_flows_client.get_templates.side_effect = [
            {
                "next": "https://flows.example.com/api/v2/templates.json?name=Example&cursor=abc123",
                "previous": None,
                "results": [other_template],
            },
            {
                "next": None,
                "previous": "https://flows.example.com/api/v2/templates.json?cursor=start",
                "results": [self.template_data],
            },
        ]

        result = self.use_case.execute(name=self.template_name, uuid=self.template_uuid)

        self.assertEqual(result, self.template_data)
        self.assertEqual(self.mock_flows_client.get_templates.call_count, 2)

        second_call_kwargs = self.mock_flows_client.get_templates.call_args_list[1]
        self.assertEqual(second_call_kwargs.kwargs.get("cursor"), "abc123")
        self.assertEqual(second_call_kwargs.kwargs.get("name"), "Example")

    def test_not_found_single_page(self):
        other_template = {
            "uuid": str(uuid.uuid4()),
            "name": "Other",
        }
        self.mock_flows_client.get_templates.return_value = {
            "next": None,
            "previous": None,
            "results": [other_template],
        }

        result = self.use_case.execute(name=self.template_name, uuid=self.template_uuid)

        self.assertIsNone(result)
        self.mock_flows_client.get_templates.assert_called_once()

    def test_not_found_multiple_pages_exhausted(self):
        self.mock_flows_client.get_templates.side_effect = [
            {
                "next": "https://flows.example.com/api/v2/templates.json?cursor=page2",
                "previous": None,
                "results": [{"uuid": str(uuid.uuid4()), "name": "A"}],
            },
            {
                "next": "https://flows.example.com/api/v2/templates.json?cursor=page3",
                "previous": None,
                "results": [{"uuid": str(uuid.uuid4()), "name": "B"}],
            },
            {
                "next": None,
                "previous": None,
                "results": [{"uuid": str(uuid.uuid4()), "name": "C"}],
            },
        ]

        result = self.use_case.execute(name=self.template_name, uuid=self.template_uuid)

        self.assertIsNone(result)
        self.assertEqual(self.mock_flows_client.get_templates.call_count, 3)

    def test_name_matches_but_uuid_does_not(self):
        wrong_uuid_template = {
            "uuid": str(uuid.uuid4()),
            "name": self.template_name,
        }
        self.mock_flows_client.get_templates.return_value = {
            "next": None,
            "previous": None,
            "results": [wrong_uuid_template],
        }

        result = self.use_case.execute(name=self.template_name, uuid=self.template_uuid)

        self.assertIsNone(result)

    def test_uuid_matches_but_name_does_not(self):
        wrong_name_template = {
            "uuid": self.template_uuid,
            "name": "Wrong Name",
        }
        self.mock_flows_client.get_templates.return_value = {
            "next": None,
            "previous": None,
            "results": [wrong_name_template],
        }

        result = self.use_case.execute(name=self.template_name, uuid=self.template_uuid)

        self.assertIsNone(result)

    def test_empty_results_list(self):
        self.mock_flows_client.get_templates.return_value = {
            "next": None,
            "previous": None,
            "results": [],
        }

        result = self.use_case.execute(name=self.template_name, uuid=self.template_uuid)

        self.assertIsNone(result)
        self.mock_flows_client.get_templates.assert_called_once()
