from typing import List, Optional
from urllib.parse import urlencode, urljoin

from django.urls import get_script_prefix


def get_ui_url(paths: List[str], params: Optional[dict] = {}) -> str:
    """"""
    root = get_script_prefix()

    url = urljoin(root, "/".join(paths))

    if params:
        params = "?" + urlencode(params)
        url = urljoin(url, params)

    return url
