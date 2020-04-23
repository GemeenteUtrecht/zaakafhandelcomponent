import logging
from typing import Union
from urllib.parse import urljoin

from django.core.exceptions import ImproperlyConfigured

import requests

from .models import FormsConfig

logger = logging.getLogger(__name__)


class OpenFormsClient:
    def __init__(self):
        config = FormsConfig.get_solo()
        if not config.forms_service:
            raise ImproperlyConfigured("No Open Forms service specified yet!")

        # Not OAS driven, so extract what we need
        _client = config.forms_service.build_client()

        # TODO: this does _not_ rewrite the URL to NLX! Could write a custom class that
        # just 'mocks' the schema with defaultdict?
        self.base_url = _client.base_url
        self.auth_header = _client.auth_header

    def request(self, method: str, path: str, **kwargs) -> Union[list, dict]:
        kwargs.setdefault("headers", {})
        kwargs["headers"].update(self.auth_header)

        if path.startswith("/"):
            logger.warning("Paths should be relative, i.e. not have leading slashes!")
            path = path[1:]

        url = urljoin(self.base_url, path)
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def get(self, path: str, params=None, **kwargs):
        return self.request("get", path, params=params, **kwargs)

    def get_forms(self):
        return self.get("forms")

    def get_form_fields(self, form_id: int):
        return self.get(f"forms/{form_id}/fields")
