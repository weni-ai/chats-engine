import logging
from typing import List, Optional

import requests
from sentry_sdk import capture_exception
from django.conf import settings
from rest_framework.exceptions import APIException


logger = logging.getLogger(__name__)


class MetaGraphAPIClient:
    base_host_url = settings.META_GRAPH_API_BASE_HOST_URL
    api_version = settings.META_GRAPH_API_VERSION
    access_token = settings.WHATSAPP_API_ACCESS_TOKEN

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
        }

    def get_templates_list(
        self,
        waba_id: str,
        name: Optional[str] = None,
        limit: int = 9999,
        fields: Optional[List[str]] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        language: Optional[str] = None,
        category: Optional[str] = None,
    ):
        url = f"{self.base_host_url}/{self.api_version}/{waba_id}/message_templates"

        params = {
            filter_name: filter_value
            for filter_name, filter_value in {
                "name": name,
                "limit": limit,
                "fields": ",".join(fields) if fields else None,
                "language": language,
                "category": category,
            }.items()
            if filter_value is not None
        }

        if before:
            params["before"] = before

        elif after:
            params["after"] = after

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=60
            )
            response.raise_for_status()
        except requests.HTTPError as err:
            logger.error(
                "Error getting templates list: %s. Original exception: %s",
                err.response.text,
                err,
                exc_info=True,
            )
            event_id = capture_exception(err)

            raise APIException(
                {"error": f"An error has occurred. Event ID: {event_id}"},
                code="meta_api_error",
            ) from err

        return response.json()
