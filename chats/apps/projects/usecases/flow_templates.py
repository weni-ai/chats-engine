import logging

import sentry_sdk

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.internal.rest_clients.meta import MetaGraphAPIClient
from chats.apps.projects.dataclass import (
    FlowTemplate,
    FlowTemplateChannel,
    FlowTemplatesData,
)
from chats.apps.projects.models import Project
from chats.apps.projects.usecases.exceptions import (
    FlowTemplateChannelsNotFound,
    FlowTemplateNotFound,
)
from chats.apps.projects.usecases.flows_templates import FlowsTemplatesUseCase
from chats.apps.projects.usecases.get_project_channels_info import (
    GetProjectChannelsInfoUseCase,
)

logger = logging.getLogger(__name__)


class GetFlowTemplatesDataUseCase:
    def __init__(self, project_uuid):
        self.project_uuid = project_uuid
        self.flows_client = FlowRESTClient()
        self.flows_templates_usecase = FlowsTemplatesUseCase(project_uuid)
        self.channels_usecase = GetProjectChannelsInfoUseCase(project_uuid)
        self.meta_client = MetaGraphAPIClient()

    def _get_flow_definition(self, flow_uuid):
        project = Project.objects.get(uuid=self.project_uuid)
        return self.flows_client.retrieve_flow_definitions(project, flow_uuid)

    TRIGGER_PARAMS_PREFIX = "@trigger.params."

    def _extract_templates_from_definition(self, definition):
        seen_uuids = set()
        templates_info = []

        for flow in definition.get("flows", []):
            for node in flow.get("nodes", []):
                for action in node.get("actions", []):
                    templating = action.get("templating")
                    if not templating:
                        continue

                    template = templating.get("template", {})
                    template_uuid = template.get("uuid")
                    template_name = template.get("name")

                    if not template_uuid or not template_name:
                        continue

                    if template_uuid in seen_uuids:
                        continue

                    seen_uuids.add(template_uuid)

                    variables = [
                        var.removeprefix(self.TRIGGER_PARAMS_PREFIX)
                        for var in templating.get("variables", [])
                        if var.startswith(self.TRIGGER_PARAMS_PREFIX)
                    ]

                    templates_info.append(
                        {
                            "uuid": template_uuid,
                            "name": template_name,
                            "variables": variables,
                        }
                    )

        return templates_info

    def _get_template_channels(self, template_info):
        template = self.flows_templates_usecase.execute(
            name=template_info["name"], uuid=template_info["uuid"]
        )
        if not template:
            return []

        channels = []
        for translation in template.get("translations", []):
            channel = translation.get("channel")
            if channel and channel.get("uuid"):
                channels.append(
                    FlowTemplateChannel(
                        uuid=channel["uuid"],
                        name=channel.get("name", ""),
                        template_name=template_info["name"],
                    )
                )

        return channels

    def _resolve_waba_id(self, template_channels, project_channels_map):
        for template_channel in template_channels:
            waba_id = project_channels_map.get(template_channel.uuid)
            if waba_id:
                return waba_id
        return None

    def _fetch_meta_template(self, waba_id, template_name):
        response = self.meta_client.get_templates_list(
            waba_id=waba_id, name=template_name
        )
        data = response.get("data", [])

        if not data:
            exc = FlowTemplateNotFound(
                f"Template '{template_name}' not found in WABA '{waba_id}'"
            )
            logger.error(
                "Template not found in Meta Graph API: waba_id=%s, name=%s",
                waba_id,
                template_name,
                exc_info=exc,
            )
            sentry_sdk.capture_exception(exc)
            raise exc

        return data[0]

    def execute(self, flow_uuid):
        definition = self._get_flow_definition(flow_uuid)
        templates_info = self._extract_templates_from_definition(definition)

        if not templates_info:
            return FlowTemplatesData(uuid=flow_uuid, templates=[])

        project_channels = self.channels_usecase.execute()
        project_channels_map = {
            ch["uuid"]: ch.get("config", {}).get("wa_waba_id")
            for ch in project_channels
        }

        for template_info in templates_info:
            template_channels = self._get_template_channels(template_info)

            if not template_channels:
                raise FlowTemplateChannelsNotFound(
                    f"No channels found for template '{template_info['name']}' "
                    f"in flow '{flow_uuid}'"
                )

            waba_id = self._resolve_waba_id(
                template_channels, project_channels_map
            )
            if not waba_id:
                continue

            meta_template = self._fetch_meta_template(
                waba_id, template_info["name"]
            )
            flow_template = FlowTemplate(
                id=meta_template["id"],
                name=meta_template["name"],
                data=meta_template,
                variables=template_info.get("variables", []),
            )
            return FlowTemplatesData(
                uuid=flow_uuid, templates=[flow_template]
            )

        return FlowTemplatesData(uuid=flow_uuid, templates=[])
