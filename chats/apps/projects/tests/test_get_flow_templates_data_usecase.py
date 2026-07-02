import uuid

from unittest.mock import Mock, patch

from django.test import TestCase

from chats.apps.projects.models import Project
from chats.apps.projects.dataclass import FlowTemplatesData
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

    def _make_flow_with_template(
        self,
        template_uuid,
        template_name,
        variables=None,
        flow_uuid=None,
    ):
        if variables is None:
            variables = [
                "@trigger.params.contactname",
                "@trigger.params.agentname",
            ]
        return {
            "uuid": flow_uuid or self.flow_uuid,
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
            ],
        }

    def _make_definition_with_template(
        self,
        template_uuid,
        template_name,
        variables=None,
        flow_uuid=None,
    ):
        return {
            "flows": [
                self._make_flow_with_template(
                    template_uuid, template_name, variables, flow_uuid
                )
            ]
        }

    def _make_flow_without_template(self, flow_uuid=None):
        return {
            "uuid": flow_uuid or self.flow_uuid,
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
            ],
        }

    def _make_definition_without_template(self):
        return {"flows": [self._make_flow_without_template()]}

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
                    "uuid": self.flow_uuid,
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
                    ],
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

    def test_execute_returns_all_valid_templates(self):
        channel_uuid_1 = str(uuid.uuid4())
        channel_uuid_2 = str(uuid.uuid4())
        template_uuid_1 = str(uuid.uuid4())
        template_uuid_2 = str(uuid.uuid4())
        other_template_name = "other_template"

        definition = {
            "flows": [
                {
                    "uuid": self.flow_uuid,
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
                                            "name": other_template_name,
                                        },
                                        "variables": [
                                            "@trigger.params.url",
                                        ],
                                    },
                                }
                            ],
                        },
                    ],
                }
            ]
        }
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        def flows_templates_side_effect(name, uuid):
            if uuid == template_uuid_1:
                return {
                    "uuid": template_uuid_1,
                    "name": self.template_name,
                    "translations": [
                        {
                            "language": "por",
                            "status": "approved",
                            "channel": {
                                "uuid": channel_uuid_1,
                                "name": "Channel 1",
                            },
                        }
                    ],
                }
            if uuid == template_uuid_2:
                return {
                    "uuid": template_uuid_2,
                    "name": other_template_name,
                    "translations": [
                        {
                            "language": "por",
                            "status": "approved",
                            "channel": {
                                "uuid": channel_uuid_2,
                                "name": "Channel 2",
                            },
                        }
                    ],
                }
            return None

        self.mock_flows_templates_usecase.execute.side_effect = (
            flows_templates_side_effect
        )

        self.mock_channels_usecase.execute.return_value = [
            self._make_project_channel(channel_uuid_1, self.waba_id),
            self._make_project_channel(channel_uuid_2, self.waba_id),
        ]

        meta_template_1 = self._make_meta_template(
            template_id="111", name=self.template_name
        )
        meta_template_2 = self._make_meta_template(
            template_id="222", name=other_template_name
        )
        self.mock_meta_client.get_templates_list.side_effect = [
            {"data": [meta_template_1]},
            {"data": [meta_template_2]},
        ]

        result = self.use_case.execute(flow_uuid=self.flow_uuid)

        self.assertEqual(len(result.templates), 2)
        self.assertEqual(result.templates[0].id, meta_template_1["id"])
        self.assertEqual(result.templates[1].id, meta_template_2["id"])
        self.assertEqual(self.mock_meta_client.get_templates_list.call_count, 2)
        self.assertEqual(self.mock_flows_templates_usecase.execute.call_count, 2)

    @patch("chats.apps.projects.usecases.flow_templates.logger")
    def test_execute_skips_template_not_found_in_meta(self, mock_logger):
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

        result = self.use_case.execute(flow_uuid=self.flow_uuid)

        self.assertEqual(result, FlowTemplatesData(uuid=self.flow_uuid, templates=[]))
        mock_logger.warning.assert_called_once()

    @patch("chats.apps.projects.usecases.flow_templates.logger")
    def test_execute_skips_stale_template_and_returns_valid_ones(self, mock_logger):
        channel_uuid_1 = str(uuid.uuid4())
        template_uuid_1 = str(uuid.uuid4())
        template_uuid_2 = str(uuid.uuid4())
        stale_template_name = "lembrete_de_agendamento_06_2024"

        definition = {
            "flows": [
                {
                    "uuid": self.flow_uuid,
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
                                            "name": stale_template_name,
                                        },
                                        "variables": [
                                            "@trigger.params.url",
                                        ],
                                    },
                                }
                            ],
                        },
                    ],
                }
            ]
        }
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        def flows_templates_side_effect(name, uuid):
            if uuid == template_uuid_1:
                return {
                    "uuid": template_uuid_1,
                    "name": self.template_name,
                    "translations": [
                        {
                            "language": "por",
                            "status": "approved",
                            "channel": {
                                "uuid": channel_uuid_1,
                                "name": "Channel 1",
                            },
                        }
                    ],
                }
            return None

        self.mock_flows_templates_usecase.execute.side_effect = (
            flows_templates_side_effect
        )

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
        mock_logger.warning.assert_called_once()
        warning_message = mock_logger.warning.call_args[0][0]
        self.assertIn("not found in flows templates", warning_message)

    def test_extract_templates_from_definition_finds_templating_in_actions(self):
        flow = self._make_flow_with_template(
            self.template_uuid, self.template_name
        )

        result = self.use_case._extract_templates_from_definition(flow)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["uuid"], self.template_uuid)
        self.assertEqual(result[0]["name"], self.template_name)
        self.assertEqual(
            result[0]["variables"], ["contactname", "agentname"]
        )

    def test_extract_templates_ignores_actions_without_templating(self):
        flow = self._make_flow_without_template()

        result = self.use_case._extract_templates_from_definition(flow)

        self.assertEqual(result, [])

    def test_extract_templates_filters_only_trigger_params_variables(self):
        flow = self._make_flow_with_template(
            self.template_uuid,
            self.template_name,
            variables=[
                "@trigger.params.contactname",
                "@(title(contact.name))",
                "@results.vendedor",
                "@trigger.params.url",
            ],
        )

        result = self.use_case._extract_templates_from_definition(flow)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["variables"], ["contactname", "url"])

    @patch("chats.apps.projects.usecases.flow_templates.logger")
    def test_execute_skips_template_not_found_in_flows(self, mock_logger):
        definition = self._make_definition_with_template(
            self.template_uuid, self.template_name
        )
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        self.mock_flows_templates_usecase.execute.return_value = None
        self.mock_channels_usecase.execute.return_value = []

        result = self.use_case.execute(flow_uuid=self.flow_uuid)

        self.assertEqual(result, FlowTemplatesData(uuid=self.flow_uuid, templates=[]))
        mock_logger.warning.assert_called_once()

    def test_get_flow_definition_filters_response_by_flow_uuid(self):
        other_flow_uuid = str(uuid.uuid4())
        other_template_uuid = str(uuid.uuid4())

        definition = {
            "flows": [
                self._make_flow_with_template(
                    other_template_uuid,
                    "other_template",
                    flow_uuid=other_flow_uuid,
                ),
                self._make_flow_with_template(
                    self.template_uuid,
                    self.template_name,
                ),
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

        result = self.use_case.execute(flow_uuid=self.flow_uuid)

        self.assertEqual(len(result.templates), 1)
        self.assertEqual(result.templates[0].id, meta_template["id"])
        self.mock_flows_templates_usecase.execute.assert_called_once_with(
            name=self.template_name, uuid=self.template_uuid
        )

    def test_get_flow_definition_returns_empty_when_no_flow_matches(self):
        definition = {
            "flows": [
                self._make_flow_with_template(
                    str(uuid.uuid4()),
                    "other_template",
                    flow_uuid=str(uuid.uuid4()),
                )
            ]
        }
        self.mock_flows_client.retrieve_flow_definitions.return_value = definition

        result = self.use_case.execute(flow_uuid=self.flow_uuid)

        self.assertEqual(result, FlowTemplatesData(uuid=self.flow_uuid, templates=[]))
        self.mock_flows_templates_usecase.execute.assert_not_called()
        self.mock_meta_client.get_templates_list.assert_not_called()
