import uuid

from unittest.mock import Mock, patch

from django.test import TestCase

from chats.apps.projects.models import Project
from chats.apps.projects.dataclass import FlowTemplatesData
from chats.apps.projects.usecases.exceptions import (
    FlowTemplateChannelsNotFound,
    FlowTemplateNotFound,
)
from chats.apps.projects.usecases.flow_templates import GetFlowTemplatesDataUseCase


class TestGetFlowTemplatesDataUseCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Test Project",
        )
        self.use_case = GetFlowTemplatesDataUseCase(project_uuid=str(self.project.uuid))

        self.mock_flows_client = Mock()
        self.mock_flows_templates_usecase = Mock()
        self.mock_channels_usecase = Mock()
        self.mock_meta_client = Mock()

        self.use_case.flows_client = self.mock_flows_client
        self.use_case.flows_templates_usecase = self.mock_flows_templates_usecase
        self.use_case.channels_usecase = self.mock_channels_usecase
        self.use_case.meta_client = self.mock_meta_client

        self.flow_uuid = str(uuid.uuid4())
        self.template_uuid = str(uuid.uuid4())
        self.template_name = "welcome_message"
        self.channel_uuid = str(uuid.uuid4())
        self.waba_id = "111222333444"

    def _make_definition_with_template(
        self,
        template_uuid,
        template_name,
        variables=None,
    ):
        if variables is None:
            variables = [
                "@trigger.params.contactname",
                "@trigger.params.agentname",
            ]
        return {
            "flows": [
                {
                    "nodes": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "actions": [
                                {
                                    "type": "send_msg",
                                    "uuid": str(uuid.uuid4()),
                                    "text": "",
                                    "templating": {
                                        "uuid": str(uuid.uuid4()),
                                        "template": {
                                            "uuid": template_uuid,
                                            "name": template_name,
                                        },
                                        "variables": variables,
                                    },
                                }
                            ],
                        }
                    ]
                }
            ]
        }

    def _make_definition_without_template(self):
        return {
            "flows": [
                {
                    "nodes": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "actions": [
                                {
                                    "type": "set_run_result",
                                    "uuid": str(uuid.uuid4()),
                                    "name": "params",
                                    "value": "@trigger.params",
                                }
                            ],
                        }
                    ]
                }
            ]
        }

    def _make_flows_template_response(self, channel_uuid, channel_name="Channel"):
        return {
            "uuid": self.template_uuid,
            "name": self.template_name,
            "translations": [
                {
                    "language": "por",
                    "content": "Hello {1}",
                    "status": "approved",
                    "channel": {
                        "uuid": channel_uuid,
                        "name": channel_name,
                    },
                }
            ],
        }

    def _make_project_channel(self, channel_uuid, waba_id):
        return {
            "uuid": channel_uuid,
            "name": "WhatsApp Channel",
            "config": {
                "wa_waba_id": waba_id,
                "wa_number": "+5511999999999",
            },
            "address": "+5511999999999",
            "is_active": True,
        }

    def _make_meta_template(self, template_id="123456", name="welcome_message"):
        return {
            "id": template_id,
            "name": name,
            "status": "APPROVED",
            "category": "MARKETING",
            "language": "pt_BR",
            "components": [{"type": "BODY", "text": "Hello {1}"}],
        }

    def test_flow_without_templates_returns_empty_list(self):
        self.mock_flows_client.retrieve_flow_definitions.return_value = (
            self._make_definition_without_template()
        )

        result = self.use_case.execute(flow_uuid=self.flow_uuid)

        self.assertEqual(result, FlowTemplatesData(uuid=self.flow_uuid, templates=[]))
        self.mock_flows_templates_usecase.execute.assert_not_called()
        self.mock_meta_client.get_templates_list.assert_not_called()

    def test_flow_with_single_template_returns_meta_data(self):
        definition = self._make_definition_with_template(
            self.template_uuid, self.template_name
        )
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        self.mock_flows_templates_usecase.execute.return_value = (
            self._make_flows_template_response(self.channel_uuid)
        )

        self.mock_channels_usecase.execute.return_value = [
            self._make_project_channel(self.channel_uuid, self.waba_id)
        ]

        meta_template = self._make_meta_template()
        self.mock_meta_client.get_templates_list.return_value = {
            "data": [meta_template]
        }

        result = self.use_case.execute(flow_uuid=self.flow_uuid)

        self.assertEqual(result.uuid, self.flow_uuid)
        self.assertEqual(len(result.templates), 1)
        self.assertEqual(result.templates[0].id, meta_template["id"])
        self.assertEqual(result.templates[0].name, meta_template["name"])
        self.assertEqual(result.templates[0].data, meta_template)
        self.assertEqual(
            result.templates[0].variables, ["contactname", "agentname"]
        )

    def test_flow_with_multiple_templates_deduplicates_by_uuid(self):
        definition = {
            "flows": [
                {
                    "nodes": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "actions": [
                                {
                                    "type": "send_msg",
                                    "uuid": str(uuid.uuid4()),
                                    "text": "",
                                    "templating": {
                                        "uuid": str(uuid.uuid4()),
                                        "template": {
                                            "uuid": self.template_uuid,
                                            "name": self.template_name,
                                        },
                                        "variables": [
                                            "@trigger.params.contactname",
                                        ],
                                    },
                                }
                            ],
                        },
                        {
                            "uuid": str(uuid.uuid4()),
                            "actions": [
                                {
                                    "type": "send_msg",
                                    "uuid": str(uuid.uuid4()),
                                    "text": "",
                                    "templating": {
                                        "uuid": str(uuid.uuid4()),
                                        "template": {
                                            "uuid": self.template_uuid,
                                            "name": self.template_name,
                                        },
                                        "variables": [
                                            "@trigger.params.agentname",
                                        ],
                                    },
                                }
                            ],
                        },
                    ]
                }
            ]
        }
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        self.mock_flows_templates_usecase.execute.return_value = (
            self._make_flows_template_response(self.channel_uuid)
        )

        self.mock_channels_usecase.execute.return_value = [
            self._make_project_channel(self.channel_uuid, self.waba_id)
        ]

        meta_template = self._make_meta_template()
        self.mock_meta_client.get_templates_list.return_value = {
            "data": [meta_template]
        }

        self.use_case.execute(flow_uuid=self.flow_uuid)

        self.mock_flows_templates_usecase.execute.assert_called_once_with(
            name=self.template_name, uuid=self.template_uuid
        )

    def test_execute_returns_only_first_valid_template(self):
        channel_uuid_1 = str(uuid.uuid4())
        template_uuid_1 = str(uuid.uuid4())
        template_uuid_2 = str(uuid.uuid4())

        definition = {
            "flows": [
                {
                    "nodes": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "actions": [
                                {
                                    "type": "send_msg",
                                    "uuid": str(uuid.uuid4()),
                                    "text": "",
                                    "templating": {
                                        "uuid": str(uuid.uuid4()),
                                        "template": {
                                            "uuid": template_uuid_1,
                                            "name": self.template_name,
                                        },
                                        "variables": [
                                            "@trigger.params.contactname",
                                        ],
                                    },
                                }
                            ],
                        },
                        {
                            "uuid": str(uuid.uuid4()),
                            "actions": [
                                {
                                    "type": "send_msg",
                                    "uuid": str(uuid.uuid4()),
                                    "text": "",
                                    "templating": {
                                        "uuid": str(uuid.uuid4()),
                                        "template": {
                                            "uuid": template_uuid_2,
                                            "name": "other_template",
                                        },
                                        "variables": [
                                            "@trigger.params.url",
                                        ],
                                    },
                                }
                            ],
                        },
                    ]
                }
            ]
        }
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        self.mock_flows_templates_usecase.execute.return_value = {
            "uuid": template_uuid_1,
            "name": self.template_name,
            "translations": [
                {
                    "language": "por",
                    "status": "approved",
                    "channel": {"uuid": channel_uuid_1, "name": "Channel 1"},
                }
            ],
        }

        self.mock_channels_usecase.execute.return_value = [
            self._make_project_channel(channel_uuid_1, self.waba_id),
        ]

        meta_template = self._make_meta_template()
        self.mock_meta_client.get_templates_list.return_value = {
            "data": [meta_template]
        }

        result = self.use_case.execute(flow_uuid=self.flow_uuid)

        self.assertEqual(len(result.templates), 1)
        self.assertEqual(result.templates[0].id, meta_template["id"])
        self.mock_meta_client.get_templates_list.assert_called_once_with(
            waba_id=self.waba_id, name=self.template_name
        )
        self.mock_flows_templates_usecase.execute.assert_called_once()

    def test_template_not_found_in_meta_raises_exception(self):
        definition = self._make_definition_with_template(
            self.template_uuid, self.template_name
        )
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        self.mock_flows_templates_usecase.execute.return_value = (
            self._make_flows_template_response(self.channel_uuid)
        )

        self.mock_channels_usecase.execute.return_value = [
            self._make_project_channel(self.channel_uuid, self.waba_id)
        ]

        self.mock_meta_client.get_templates_list.return_value = {"data": []}

        with self.assertRaises(FlowTemplateNotFound):
            self.use_case.execute(flow_uuid=self.flow_uuid)

    @patch("chats.apps.projects.usecases.flow_templates.sentry_sdk.capture_exception")
    @patch("chats.apps.projects.usecases.flow_templates.logger")
    def test_template_not_found_logs_and_captures_sentry(
        self, mock_logger, mock_capture
    ):
        definition = self._make_definition_with_template(
            self.template_uuid, self.template_name
        )
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        self.mock_flows_templates_usecase.execute.return_value = (
            self._make_flows_template_response(self.channel_uuid)
        )

        self.mock_channels_usecase.execute.return_value = [
            self._make_project_channel(self.channel_uuid, self.waba_id)
        ]

        self.mock_meta_client.get_templates_list.return_value = {"data": []}

        with self.assertRaises(FlowTemplateNotFound):
            self.use_case.execute(flow_uuid=self.flow_uuid)

        mock_capture.assert_called_once()
        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args
        self.assertIn("exc_info", call_kwargs.kwargs)

    def test_extract_templates_from_definition_finds_templating_in_actions(self):
        definition = self._make_definition_with_template(
            self.template_uuid, self.template_name
        )

        result = self.use_case._extract_templates_from_definition(definition)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["uuid"], self.template_uuid)
        self.assertEqual(result[0]["name"], self.template_name)
        self.assertEqual(
            result[0]["variables"], ["contactname", "agentname"]
        )

    def test_extract_templates_ignores_actions_without_templating(self):
        definition = self._make_definition_without_template()

        result = self.use_case._extract_templates_from_definition(definition)

        self.assertEqual(result, [])

    def test_extract_templates_filters_only_trigger_params_variables(self):
        definition = self._make_definition_with_template(
            self.template_uuid,
            self.template_name,
            variables=[
                "@trigger.params.contactname",
                "@(title(contact.name))",
                "@results.vendedor",
                "@trigger.params.url",
            ],
        )

        result = self.use_case._extract_templates_from_definition(definition)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["variables"], ["contactname", "url"])

    def test_no_template_channels_found_raises_exception(self):
        definition = self._make_definition_with_template(
            self.template_uuid, self.template_name
        )
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        self.mock_flows_templates_usecase.execute.return_value = None
        self.mock_channels_usecase.execute.return_value = []

        with self.assertRaises(FlowTemplateChannelsNotFound):
            self.use_case.execute(flow_uuid=self.flow_uuid)
