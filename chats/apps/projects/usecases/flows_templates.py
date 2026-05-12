import logging
from urllib.parse import urlparse, parse_qs

from django.conf import settings
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.projects.models import Project

logger = logging.getLogger(__name__)

MAX_PAGES = settings.FLOWS_TEMPLATES_MAX_PAGES


class FlowsTemplatesUseCase:
    def __init__(self, project_uuid):
        self.project_uuid = project_uuid
        self.flows_client = FlowRESTClient()

    def _parse_next_url(self, next_url):
        parsed = urlparse(next_url)
        params = {
            key: value[0] if len(value) == 1 else value
            for key, value in parse_qs(parsed.query).items()
        }
        return params

    def execute(self, name, uuid):
        project = Project.objects.get(uuid=self.project_uuid)
        extra_kwargs = {
            "name": name,
            "uuid": uuid,
        }

        for _ in range(MAX_PAGES):
            response = self.flows_client.get_templates(project, **extra_kwargs)

            for template in response.get("results", []):
                if template.get("name") == name and template.get("uuid") == uuid:
                    return template

            next_url = response.get("next")
            if not next_url:
                return None

            extra_kwargs = self._parse_next_url(next_url)
