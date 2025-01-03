from numbers import Number

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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
