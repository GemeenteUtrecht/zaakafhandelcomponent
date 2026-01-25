"""
ZGW API Client - Backward compatibility wrapper.

This module provides backward compatibility by importing from the new modular architecture.
The ZGWClient implementation has been refactored into zac.zgw with a clean, composable design.

New architecture (zac.zgw):
- client.py: Main ZGWClient built on composition
- schema/: Schema loading and caching
- operations/: Operation resolution and execution
- resources/: CRUD operations
- utils/: URL normalization and error handling
- compat/: Backward compatibility utilities

For new code, import from zac.zgw:
    from zac.zgw import ZGWClient

For existing code, this module maintains the old import path:
    from zac.zgw_client import ZGWClient  # Still works
"""

from urllib.parse import parse_qs, urlparse

# Import from new architecture
from zac.zgw import ZGWClient
# Re-export exception classes for backward compatibility
from zac.zgw_client_old import MultipleServices, NoAuth, NoService

__all__ = [
    "ZGWClient",
    "NoService",
    "MultipleServices",
    "NoAuth",
    "get_paginated_results",
]


def get_paginated_results(
    client: ZGWClient, resource: str, minimum=None, *args, **kwargs
) -> list:
    """
    Fetch all results from a paginated API endpoint.

    This is a compatibility wrapper that fetches all pages of results from a
    paginated ZGW API endpoint.

    Args:
        client: The ZGWClient instance
        resource: The resource name (e.g., "zaak", "zaaktype")
        minimum: Optional minimum number of results to fetch before stopping
        *args: Additional positional arguments passed to client.list()
        **kwargs: Additional keyword arguments passed to client.list()

    Returns:
        List of all results from all pages

    Examples:
        >>> all_zaken = get_paginated_results(client, "zaak", query_params={"status": "open"})
        >>> limited_results = get_paginated_results(client, "zaak", minimum=50)
    """
    query_params = kwargs.get("query_params", {})

    results = []
    response = client.list(resource, *args, **kwargs)

    results += response["results"]

    if minimum and len(results) >= minimum:
        return results

    while response.get("next"):
        next_url = urlparse(response["next"])
        query = parse_qs(next_url.query)
        new_page = int(query["page"][0])
        query_params["page"] = [new_page]
        kwargs["query_params"] = query_params
        response = client.list(resource, *args, **kwargs)
        results += response["results"]

        if minimum and len(results) >= minimum:
            return results

    return results
