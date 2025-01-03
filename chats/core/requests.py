from numbers import Number
import time
from typing import Callable

import requests
from requests.adapters import HTTPAdapter
from requests.models import Response
from sentry_sdk import capture_exception
from urllib3.util.retry import Retry

from django.conf import settings


def get_request_session_with_retries(
    retries: int = 5,
    backoff_factor: Number = 0.1,
    status_forcelist: list = [],
    method_whitelist: list = [],
) -> requests.Session:
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        method_whitelist=method_whitelist,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def request_with_retry(
    request_method: Callable,
    request_kwargs: dict,
    attempts: int = 5,
    wait_time: int = 1,
    backoff_factor: int = 1,
) -> Response:
    exception = None

    for _ in range(attempts):
        try:
            response: Response = request_method(**request_kwargs)
            response.raise_for_status()

        except requests.HTTPError as exp:
            wait_time *= backoff_factor
            exception = exp

            time.sleep(wait_time)
        else:
            return response

    if exception and settings.USE_SENTRY:
        capture_exception(exception)

    return None
