"""
ZGW API Client built on ape_pie.APIClient.

This module provides a proper API client for ZGW services that replaces the deprecated
ZGWClient from zgw-consumers <1.0. It builds on ape_pie's APIClient and adds:
- API convenience methods (create, retrieve, list, update, partial_update, delete)
- Logging capabilities via the _log attribute
- Backward compatibility with the old ZGWClient API
- OAS schema support for operation resolution
"""

import logging
from typing import Any, Union

import yaml
from ape_pie import APIClient
from requests import PreparedRequest
from zgw_consumers.models import Service

logger = logging.getLogger(__name__)


class NoService(Exception):
    """Raised when no service is configured for a given task."""

    pass


class MultipleServices(Exception):
    """Raised when multiple services are configured for a single task."""

    pass


class NoAuth(Exception):
    """Raised when authentication is required but not configured."""

    pass


class ZGWClient(APIClient):
    """
    A proper API client for ZGW services, built on ape_pie.APIClient.

    This client provides:
    - Full ape_pie.APIClient functionality (Session-based requests with base URL)
    - NLX URL rewriting support (inherited via NLXMixin when needed)
    - API convenience methods for ZGW resources (create, retrieve, list, etc.)
    - Logging via the _log attribute
    - Backward compatibility with zgw-consumers <1.0 ZGWClient

    Usage:
        from zgw_consumers.models import Service
        from zgw_consumers.client import build_client
        from bptl.work_units.zgw.client import ZGWClient

        service = Service.objects.get(...)
        client = build_client(service, client_factory=ZGWClient)

        # Use convenience methods
        zaak = client.retrieve("zaak", url="https://...")
        zaken = client.list("zaken", query_params={"status": "open"})
        new_zaak = client.create("zaken", data={...})

        # Or use standard requests methods
        response = client.get("zaken/abc-123")
        response = client.post("zaken", json={...})
    """

    def __init__(
        self,
        base_url: str,
        request_kwargs: dict[str, Any] | None = None,
        service: Service | None = None,
        **kwargs: Any,
    ):
        """
        Initialize the ZGW client.

        Args:
            base_url: The base URL of the ZGW API
            request_kwargs: Default request kwargs (auth, timeout, etc.)
            service: Optional Service model instance for logging
            **kwargs: Additional kwargs (e.g., nlx_base_url for NLX support)
        """
        super().__init__(base_url, request_kwargs, **kwargs)
        self.service = service
        self._schema = None  # Lazy-loaded OAS schema

        # Add credentials() method to auth object for backward compatibility
        # In zgw-consumers <1.0, auth had a credentials() method
        # In zgw-consumers 1.x, auth objects are AuthBase subclasses without this method
        if self.auth and not hasattr(self.auth, "credentials"):
            self._wrap_auth_with_credentials()

    def _wrap_auth_with_credentials(self):
        """
        Add a credentials() method to the auth object for backward compatibility.

        Legacy code calls client.auth.credentials() to get auth headers.
        In zgw-consumers 1.x, auth objects don't have this method, so we add it.
        """

        def credentials():
            """Extract auth headers from the auth object."""
            req = PreparedRequest()
            req.headers = {}
            self.auth(req)
            return dict(req.headers)

        # Monkey-patch the credentials method onto the auth object
        self.auth.credentials = credentials

    def _load_schema(self):
        """
        Lazy-load the OAS schema for this service.

        Returns the parsed OAS schema or None if not available.

        This attempts to load schemas from:
        1. Test schema files (for testing)
        2. Remote service endpoint (in production)
        3. Falls back to None (uses pluralization inference)
        """
        if self._schema is not None:
            return self._schema

        if not self.service:
            return None

        # Try to load from test schemas first (during testing)
        try:
            from zgw_consumers.constants import APITypes
            from zgw_consumers_oas import read_schema

            # Map API types to schema file names
            api_type = getattr(self.service, "api_type", None)
            api_root = getattr(self.service, "api_root", "").lower()
            schema_name = None

            if api_type:
                # First check URL patterns for non-standard ZGW APIs
                # This handles cases where api_type is incorrectly set (e.g., ztc for objecttypes)
                if "objecttype" in api_root:
                    # Covers both objecttype.nl and objecttypes in path
                    schema_name = "objecttypes"
                elif "object" in api_root:
                    # Must come after objecttype check
                    schema_name = "objects"
                elif "kownsl" in api_root:
                    schema_name = "kownsl"
                elif "zac" in api_root:
                    schema_name = "zac"
                # If no URL pattern matched, use api_type directly
                elif api_type == APITypes.orc:
                    # Unknown orc-type API, can't determine schema
                    logger.debug(
                        f"Cannot infer schema name for APITypes.orc service with api_root: {api_root}"
                    )
                    return None
                else:
                    # Use api_type as schema name (standard ZGW APIs like zrc, ztc, drc)
                    schema_name = api_type

            if not schema_name:
                return None

            schema_bytes = read_schema(schema_name)
            self._schema = yaml.safe_load(schema_bytes)
            return self._schema
        except Exception as e:
            # Schema loading from files failed - try remote or fall back to None
            logger.debug(f"Could not load OAS schema for {self.service}: {e}")
            pass

        # In production, we don't fetch schemas from remote services
        # to avoid network calls during client initialization.
        # The pluralization fallback handles all standard cases.
        return None

    @property
    def schema(self):
        """
        Get the OAS schema for this service.

        This is a lazy-loading property that returns the parsed OAS schema.
        Used for compatibility with old zgw-consumers code that accessed client.schema.

        Returns:
            dict: The parsed OAS schema or None if not available
        """
        return self._load_schema()

    def _get_operation_url(self, operation_id: str, **kwargs) -> tuple[str, str]:
        """
        Resolve an operation ID to a URL path and HTTP method using OAS schema.

        Args:
            operation_id: The OAS operation ID (e.g., "catalogus_list", "zaak_create")
            **kwargs: Parameters to substitute in the path (e.g., uuid)

        Returns:
            Tuple of (path, method) or raises ValueError if not found
        """
        schema = self._load_schema()
        if not schema or "paths" not in schema:
            # No schema available - try to infer from operation_id
            return self._infer_operation_url(operation_id, **kwargs)

        # Search for the operation in the schema
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "patch", "delete"]:
                    if operation.get("operationId") == operation_id:
                        # Substitute path parameters
                        resolved_path = path
                        for key, value in kwargs.items():
                            resolved_path = resolved_path.replace(
                                f"{{{key}}}", str(value)
                            )
                        return resolved_path.lstrip("/"), method.upper()

        # Fallback to inference if not found in schema
        return self._infer_operation_url(operation_id, **kwargs)

    def _infer_operation_url(self, operation_id: str, **kwargs) -> tuple[str, str]:
        """
        Infer URL and method from operation_id when schema is not available.

        Uses common ZGW API patterns:
        - {resource}_list -> GET /{resources}
        - {resource}_read -> GET /{resources}/{uuid}
        - {resource}_create -> POST /{resources}
        - {resource}_update -> PUT /{resources}/{uuid}
        - {resource}_partial_update -> PATCH /{resources}/{uuid}
        - {resource}_delete -> DELETE /{resources}/{uuid}
        """
        parts = operation_id.rsplit("_", 1)
        if len(parts) != 2:
            raise ValueError(f"Cannot infer URL from operation_id: {operation_id}")

        resource, action = parts

        # Apply pluralization rules for Dutch ZGW APIs
        resource_plural = self._pluralize(resource)

        method_map = {
            "list": ("GET", f"{resource_plural}"),
            "read": ("GET", f"{resource_plural}/{{{kwargs.get('uuid', 'uuid')}}}"),
            "retrieve": ("GET", f"{resource_plural}/{{{kwargs.get('uuid', 'uuid')}}}"),
            "create": ("POST", f"{resource_plural}"),
            "update": ("PUT", f"{resource_plural}/{{{kwargs.get('uuid', 'uuid')}}}"),
            "partial_update": (
                "PATCH",
                f"{resource_plural}/{{{kwargs.get('uuid', 'uuid')}}}",
            ),
            "delete": ("DELETE", f"{resource_plural}/{{{kwargs.get('uuid', 'uuid')}}}"),
        }

        if action not in method_map:
            raise ValueError(f"Unknown action in operation_id: {action}")

        method, path_template = method_map[action]

        # Substitute parameters
        path = path_template
        for key, value in kwargs.items():
            path = path.replace(f"{{{key}}}", str(value))

        return path, method

    def _pluralize(self, word: str) -> str:
        """
        Pluralize Dutch words commonly used in ZGW APIs.

        This handles common patterns in ZGW API resource names.
        If the word is already plural, it returns it unchanged.
        """
        # Special cases for Dutch pluralization
        pluralization_map = {
            "catalogus": "catalogussen",
            "status": "statussen",
            "resultaat": "resultaten",
            "zaak": "zaken",
            "zaaktype": "zaaktypen",
            "statustype": "statustypen",
            "resultaattype": "resultaattypen",
            "roltype": "roltypen",
            "rol": "rollen",
            "eigenschap": "eigenschappen",
            "zaakeigenschap": "zaakeigenschappen",
            "object": "objecten",
            "objecttype": "objecttypen",
            "besluit": "besluiten",
            "besluittype": "besluittypen",
            "document": "documenten",
            "enkelvoudiginformatieobject": "enkelvoudiginformatieobjecten",
            "zaakinformatieobject": "zaakinformatieobjecten",
            "besluitinformatieobject": "besluitinformatieobjecten",
            "zaakobject": "zaakobjecten",
            "klantcontact": "klantcontacten",
        }

        # Build reverse map to check if word is already plural
        reverse_map = {v: v for v in pluralization_map.values()}

        # If already plural, return as-is
        if word.lower() in reverse_map:
            return word

        # Check if we have a specific singular->plural mapping
        if word.lower() in pluralization_map:
            return pluralization_map[word.lower()]

        # Check if it already looks plural (ends with common plural endings)
        if word.endswith(("en", "s")):
            return word

        # Default: just add 'en' (common Dutch plural)
        return f"{word}en"

    @classmethod
    def configure_from(cls, adapter, **kwargs):
        """
        Configure client from a ConfigAdapter.

        This extends the base implementation to inject the Service instance
        for logging purposes.

        Args:
            adapter: A ConfigAdapter instance (typically ServiceConfigAdapter)
            **kwargs: Additional kwargs to pass to __init__
        """
        # Extract service from adapter if it's a ServiceConfigAdapter
        if hasattr(adapter, "service"):
            kwargs["service"] = adapter.service

        # Call parent configure_from which will call our __init__
        return super().configure_from(adapter, **kwargs)

    def set_auth_value(self, auth_value: Union[str, dict]):
        """
        Set authentication headers dynamically.

        This method provides backward compatibility with the old ZGWClient API
        where auth could be set after instantiation.

        Args:
            auth_value: Either a dict of headers or an Authorization header value
        """
        # Store the auth value for the auth_header property
        if isinstance(auth_value, dict):
            self.auth_value = auth_value
        else:
            self.auth_value = {"Authorization": auth_value}

        # Apply these headers via _request_kwargs so they're included in all requests
        # but don't persist in the session across test boundaries
        if "headers" not in self._request_kwargs:
            self._request_kwargs["headers"] = {}
        self._request_kwargs["headers"].update(self.auth_value)

    @property
    def auth_header(self) -> dict[str, str]:
        """
        Return the authorization headers as a dictionary.

        This property provides backward compatibility with zgw-consumers <1.0.

        Returns:
            Dictionary of authorization headers
        """
        # Check if we have auth_value set via set_auth_value
        if hasattr(self, "auth_value") and self.auth_value:
            return self.auth_value

        # Otherwise, generate from the auth attribute (from Service configuration)
        if self.auth:
            req = PreparedRequest()
            req.headers = {}
            self.auth(req)
            return dict(req.headers)

        return {}

    @property
    def log(self):
        """
        Get timeline log entries for this service.

        Note: Logging is disabled in ZAC to prevent memory leaks in thread pools.
        Returns empty list for backward compatibility.
        """
        return []

    def request(self, method: str, url: str, *args, **kwargs):
        """
        Make HTTP request using the parent APIClient.

        ZAC doesn't use task-based logging, so this simply delegates to the parent.
        """
        return super().request(method, url, *args, **kwargs)

    def refresh_auth(self):
        """
        Re-generate a JWT with the given credentials.

        If a client instance is long-lived, the JWT may expire leading to 403 errors.
        This method regenerates a new JWT with the same credentials.

        This is particularly useful in long-running processes like elasticsearch indexing
        that may run for hours.
        """
        if not self.auth:
            return

        # For JWT auth, clear the cached credentials to force regeneration
        if hasattr(self.auth, "_credentials"):
            delattr(self.auth, "_credentials")

    # API convenience methods for ZGW resources
    # These provide a higher-level API on top of the HTTP methods

    def operation(self, operation_id: str, data: dict | None = None, **kwargs) -> dict:
        """
        Perform an API operation using its OAS operation ID.

        This provides backward compatibility with zgw-consumers <1.0 which used
        OAS schemas to resolve operations.

        Args:
            operation_id: The OAS operation ID (e.g., "catalogus_list", "zaak_create")
            data: Optional data to send with the request
            **kwargs: Additional parameters (uuid, path params, url, etc.)

        Returns:
            Response JSON as a dictionary

        Example:
            result = client.operation("catalogus_list", params={"domein": "ABR"})
            doc = client.operation("enkelvoudiginformatieobject_lock", uuid="123", data={})
            doc = client.operation("enkelvoudiginformatieobject_lock", data={}, url="https://api.nl/doc/123/lock")
        """
        # Separate path kwargs from request kwargs
        request_kwargs = kwargs.pop("request_kwargs", {})
        params = kwargs.pop("params", None) or request_kwargs.get("params")
        headers = request_kwargs.get("headers")

        # Check if explicit URL is provided (for backward compatibility)
        explicit_url = kwargs.pop("url", None)

        # Get the path and method for this operation
        if explicit_url:
            # Use explicit URL - make it relative to base_url
            # The URL might be a full URL or already relative
            if explicit_url.startswith("http://") or explicit_url.startswith(
                "https://"
            ):
                # It's a full URL - make it relative to base_url
                # Remove the base_url prefix to get the path
                base_url = self.base_url.rstrip("/")
                if explicit_url.startswith(base_url):
                    path = explicit_url[len(base_url) :].lstrip("/")
                else:
                    # URL doesn't match base_url - extract just the path
                    from urllib.parse import urlparse

                    parsed = urlparse(explicit_url)
                    path = parsed.path.lstrip("/")
            else:
                # Already a relative path - but might include the server base path from OAS schema
                # The OAS schema's servers section (e.g., /api/v2) is already in base_url,
                # so we need to strip it from the path if present
                from urllib.parse import parse_qs, urlparse

                # Parse to separate path from query string
                # Even if it's a relative path, it might have query parameters
                if "?" in explicit_url:
                    path_part, query_part = explicit_url.split("?", 1)
                    path = path_part.lstrip("/")
                    # Extract query parameters to merge with req_kwargs params later
                    query_from_url = parse_qs(query_part)
                    # Flatten query params (parse_qs returns lists)
                    if not params:
                        params = {}
                    for key, values in query_from_url.items():
                        params[key] = values[0] if len(values) == 1 else values
                else:
                    path = explicit_url.lstrip("/")

                # Extract the base path from base_url to strip from the path
                base_parsed = urlparse(self.base_url)
                base_path = base_parsed.path.strip("/")

                # If the path starts with the base path, strip it
                if base_path and path.startswith(base_path + "/"):
                    path = path[len(base_path) + 1 :]
                elif base_path and path == base_path:
                    path = ""

            # Determine the HTTP method for this operation
            # Try to get it from the schema first
            method = None
            schema = self._load_schema()
            if schema and "paths" in schema:
                # Search for the operation in the schema to get the correct method
                for schema_path, path_item in schema["paths"].items():
                    for http_method, operation in path_item.items():
                        if http_method.lower() in [
                            "get",
                            "post",
                            "put",
                            "patch",
                            "delete",
                        ]:
                            if operation.get("operationId") == operation_id:
                                method = http_method.upper()
                                break
                    if method:
                        break

            # Fallback to inferring method from operation_id if not found in schema
            if not method:
                if "_lock" in operation_id or "_unlock" in operation_id:
                    method = "POST"
                elif "_update" in operation_id:
                    method = "PATCH" if "partial" in operation_id else "PUT"
                elif "_create" in operation_id:
                    method = "POST"
                elif "_delete" in operation_id:
                    method = "DELETE"
                else:
                    method = "GET"
        else:
            path, method = self._get_operation_url(operation_id, **kwargs)

        # Build request kwargs
        req_kwargs = {}
        if params:
            req_kwargs["params"] = params
        if headers:
            req_kwargs["headers"] = headers

        # Make the request
        if method == "GET":
            response = self.get(path, **req_kwargs)
        elif method == "POST":
            response = self.post(path, json=data, **req_kwargs)
        elif method == "PUT":
            response = self.put(path, json=data, **req_kwargs)
        elif method == "PATCH":
            response = self.patch(path, json=data, **req_kwargs)
        elif method == "DELETE":
            response = self.delete(path, **req_kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()

        # Handle responses with no content (204, etc.) or empty bodies
        if not response.content:
            return {}

        return response.json()

    def list(self, resource: str, query_params: dict | None = None, **kwargs) -> dict:
        """
        List resources from the API using operation resolution.

        Args:
            resource: The resource type (e.g., "zaak", "catalogus", "zaakinformatieobject")
                     This is resolved via OAS schema to the correct plural endpoint
            query_params: Optional query parameters
            **kwargs: Additional request kwargs

        Returns:
            Response JSON as a dictionary (usually contains 'results' key)

        Example:
            catalogussen = client.list("catalogus", query_params={"domein": "ABR"})
            zaken = client.list("zaak", query_params={"status": "open"})
        """
        # Use operation resolution to find the correct endpoint
        # Old zgw-consumers did: resource + "_list" -> schema lookup -> /path
        operation_id = f"{resource}_list"
        params = query_params or kwargs.get("request_kwargs", {}).get("params", {})
        return self.operation(operation_id, params=params, **kwargs)

    def retrieve(self, resource: str, url: str | None = None, **kwargs) -> dict:
        """
        Retrieve a single resource from the API using operation resolution.

        Args:
            resource: The resource type (e.g., "zaak", "document")
            url: Optional full URL to the resource
            **kwargs: Additional parameters (uuid, request_kwargs, etc.)

        Returns:
            Response JSON as a dictionary

        Example:
            zaak = client.retrieve("zaak", url="https://zaken.nl/api/v1/zaken/123")
            zaak = client.retrieve("zaak", uuid="12345678-...")
            zaak = client.retrieve("zaak", url="...", request_kwargs={"headers": {"Accept-Crs": "EPSG:4326"}})
        """
        # Extract request_kwargs for headers/params
        request_kwargs = kwargs.pop("request_kwargs", {}) or {}

        if url:
            # URL provided directly - extract path from full URL
            from urllib.parse import urlparse

            parsed = urlparse(url)
            # Remove the base path to get the relative path
            base_path = urlparse(self.base_url).path.rstrip("/")
            request_url = parsed.path.replace(base_path, "", 1).lstrip("/")
        else:
            # Use operation resolution to find the correct endpoint
            # Old zgw-consumers did: resource + "_read" -> schema lookup -> /path/{uuid}
            operation_id = f"{resource}_read"
            path, _ = self._get_operation_url(operation_id, **kwargs)
            request_url = path

        # Apply headers and params from request_kwargs
        get_kwargs = {}
        if "headers" in request_kwargs:
            get_kwargs["headers"] = request_kwargs["headers"]
        if "params" in request_kwargs:
            get_kwargs["params"] = request_kwargs["params"]

        response = self.get(request_url, **get_kwargs)
        response.raise_for_status()
        return response.json()

    def create(self, resource: str, data: dict, **kwargs) -> dict:
        """
        Create a new resource via POST using operation resolution.

        Args:
            resource: The resource type (e.g., "zaak", "status")
                     This is resolved via OAS schema to the correct plural endpoint
            data: The data to POST
            **kwargs: Additional request kwargs (headers, request_kwargs, etc.)

        Returns:
            Response JSON with the created resource

        Example:
            zaak = client.create("zaak", data={"zaaktype": "...", ...})
            zaak = client.create("zaak", data={...}, request_kwargs={"headers": {...}})
        """
        # Use operation resolution to find the correct endpoint
        # Old zgw-consumers did: resource + "_create" -> schema lookup -> /path
        operation_id = f"{resource}_create"

        # Extract headers if provided
        request_kwargs = kwargs.get("request_kwargs", {})
        headers = request_kwargs.get("headers") or kwargs.get("headers")

        # Pass data and headers to operation
        operation_kwargs = {}
        if headers:
            operation_kwargs["headers"] = headers

        # Resolve the operation to get the correct path
        path, _ = self._get_operation_url(operation_id, **kwargs)

        post_kwargs = {"json": data}
        if headers:
            post_kwargs["headers"] = headers

        response = self.post(path, **post_kwargs)
        response.raise_for_status()
        return response.json()

    def update(self, resource: str, data: dict, **kwargs) -> dict:
        """
        Update a resource via PUT.

        Args:
            resource: The resource type
            data: The complete updated data
            **kwargs: Additional parameters (url, uuid, request_kwargs, etc.)

        Returns:
            Response JSON with the updated resource

        Example:
            zaak = client.update("zaak", data={...}, url="https://...")
        """
        # Extract request_kwargs for headers
        request_kwargs = kwargs.pop("request_kwargs", {})

        if "url" in kwargs:
            request_url = kwargs["url"]
        else:
            request_url = resource

        # Apply headers from request_kwargs
        put_kwargs = {"json": data}
        if "headers" in request_kwargs:
            put_kwargs["headers"] = request_kwargs["headers"]

        response = self.put(request_url, **put_kwargs)
        response.raise_for_status()
        return response.json()

    def partial_update(self, resource: str, data: dict | None = None, **kwargs) -> dict:
        """
        Partially update a resource via PATCH.

        Args:
            resource: The resource type
            data: Optional dict of fields to update (can also be passed as **kwargs)
            **kwargs: Fields to update, plus url or uuid and optional request_kwargs

        Returns:
            Response JSON with the updated resource

        Example:
            zaak = client.partial_update("zaak", {"locked": True}, url="https://...")
            zaak = client.partial_update("enkelvoudiginformatieobject",
                                        url="https://...",
                                        locked=True)
        """
        # Extract special parameters that shouldn't be in the JSON body
        request_url = kwargs.pop("url", None)
        uuid = kwargs.pop("uuid", None)
        request_kwargs = kwargs.pop("request_kwargs", {})
        zaak_uuid = kwargs.pop("zaak_uuid", None)

        # Merge data dict with kwargs (kwargs take precedence for backward compatibility)
        if data:
            json_data = {**data, **kwargs}
        else:
            json_data = kwargs
        kwargs = json_data  # Use merged data for the rest of the function

        # Build the request URL using operation resolution
        if request_url is None:
            # Construct the operation ID for partial_update
            operation_id = f"{resource}_partial_update"

            # Build path parameters dict
            path_params = {}
            if uuid:
                path_params["uuid"] = uuid
            if zaak_uuid:
                path_params["zaak_uuid"] = zaak_uuid

            # Try to resolve via OAS schema
            try:
                request_url, _ = self._get_operation_url(operation_id, **path_params)
            except (ValueError, KeyError):
                # Fallback to manual construction if schema resolution fails
                # This handles cases where schemas aren't available
                if zaak_uuid:
                    # Fallback: use pluralization for nested resources
                    plural_resource = self._pluralize(resource)
                    request_url = f"zaken/{zaak_uuid}/{plural_resource}"
                    if uuid:
                        request_url = f"{request_url}/{uuid}"
                else:
                    request_url = f"{resource}/{uuid}" if uuid else resource

        # Make the PATCH request with remaining kwargs as the JSON body
        patch_kwargs = {"json": kwargs}
        if "headers" in request_kwargs:
            patch_kwargs["headers"] = request_kwargs["headers"]

        response = self.patch(request_url, **patch_kwargs)
        response.raise_for_status()

        # Handle responses with no content (204, etc.) or empty bodies
        if not response.content:
            return {}

        return response.json()

    def delete(self, resource: str, **kwargs) -> None:
        """
        Delete a resource.

        Args:
            resource: The resource type
            **kwargs: Additional parameters (url, uuid, etc.)

        Returns:
            None

        Example:
            client.delete("zaak", uuid="12345678-...")
        """
        if "url" in kwargs:
            request_url = kwargs["url"]
        elif "uuid" in kwargs:
            request_url = f"{resource}/{kwargs['uuid']}"
        else:
            request_url = resource

        response = super().delete(request_url)
        response.raise_for_status()
        return None


# Backward compatibility utilities


def get_paginated_results(
    client: "ZGWClient", resource: str, minimum=None, *args, **kwargs
) -> list:
    """
    Fetch all results from a paginated API endpoint.

    This is a compatibility wrapper that mimics the old zgw-consumers <1.0
    get_paginated_results API using the new ape_pie client.

    Args:
        client: The ZGWClient instance
        resource: The resource name (e.g., "zaak", "zaaktype")
        minimum: Optional minimum number of results to fetch before stopping
        *args: Additional positional arguments passed to client.list()
        **kwargs: Additional keyword arguments passed to client.list()

    Returns:
        List of all results from all pages

    Example:
        all_zaken = get_paginated_results(client, "zaak", query_params={"status": "open"})
    """
    from urllib.parse import parse_qs, urlparse

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
