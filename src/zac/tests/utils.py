import os

from requests_mock import Mocker

MOCK_FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "schemas",)


def mock_service_oas_get(
    m: Mocker, service: str, url: str = None, oas_url: str = None
) -> None:
    file_name = f"{service}.yaml"
    file = os.path.join(MOCK_FILES_DIR, file_name)
    if not oas_url:
        oas_url = f"{url}schema/openapi.yaml?v=3"

    with open(file, "rb") as api_spec:
        m.get(oas_url, content=api_spec.read())
