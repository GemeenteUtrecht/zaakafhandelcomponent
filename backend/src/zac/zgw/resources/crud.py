"""
CRUD operations for ZGW API resources.

This module provides high-level convenience methods for creating, reading,
updating, and deleting resources via the ZGW API.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ape_pie import APIClient

    from zac.zgw.operations.executor import OperationExecutor
    from zac.zgw.operations.pluralization import PluralizationService
    from zac.zgw.operations.resolver import OperationResolver
    from zac.zgw.utils.url_normalizer import URLNormalizer


class ResourceCRUD:
    """
    High-level CRUD operations for ZGW API resources.

    This class provides convenience methods that use operation resolution
    and proper error handling to interact with ZGW APIs.
    """

    def __init__(
        self,
        client: "APIClient",
        resolver: "OperationResolver",
        executor: "OperationExecutor",
        normalizer: "URLNormalizer",
        pluralizer: "PluralizationService",
    ):
        """
        Initialize the ResourceCRUD.

        Args:
            client: The APIClient instance for direct HTTP calls
            resolver: OperationResolver for resolving operation IDs
            executor: OperationExecutor for executing HTTP requests
            normalizer: URLNormalizer for path normalization
            pluralizer: PluralizationService for resource name pluralization
        """
        self.client = client
        self.resolver = resolver
        self.executor = executor
        self.normalizer = normalizer
        self.pluralizer = pluralizer

    def list(self, resource: str, query_params: dict | None = None, **kwargs) -> dict:
        """
        List resources from the API using operation resolution.

        Args:
            resource: The resource type (e.g., "zaak", "catalogus")
            query_params: Optional query parameters
            **kwargs: Additional request kwargs

        Returns:
            Response JSON as a dictionary (usually contains 'results' key)

        Examples:
            >>> crud = ResourceCRUD(client, resolver, executor, normalizer, pluralizer)
            >>> catalogussen = crud.list("catalogus", query_params={"domein": "ABR"})
            >>> zaken = crud.list("zaak", query_params={"status": "open"})
        """
        operation_id = f"{resource}_list"
        params = query_params or kwargs.get("request_kwargs", {}).get("params", {})

        # Resolve operation to path and method
        path, method = self.resolver.resolve_operation(operation_id)

        # Extract headers if provided
        request_kwargs = kwargs.get("request_kwargs", {})
        headers = request_kwargs.get("headers") if request_kwargs else None

        # Execute the request
        return self.executor.execute(method, path, params=params, headers=headers)

    def retrieve(self, resource: str, url: str | None = None, **kwargs) -> dict:
        """
        Retrieve a single resource from the API.

        Args:
            resource: The resource type (e.g., "zaak", "document")
            url: Optional full URL to the resource
            **kwargs: Additional parameters (uuid, request_kwargs, etc.)

        Returns:
            Response JSON as a dictionary

        Examples:
            >>> crud.retrieve("zaak", url="https://zaken.nl/api/v1/zaken/123")
            >>> crud.retrieve("zaak", uuid="12345678-...")
        """
        # Extract request_kwargs for headers/params
        request_kwargs = kwargs.pop("request_kwargs", {}) or {}

        if url:
            # URL provided directly - normalize to path
            path = self.normalizer.normalize_to_path(url)
        else:
            # Use operation resolution to find the correct endpoint
            operation_id = f"{resource}_read"
            path, _ = self.resolver.resolve_operation(operation_id, **kwargs)

        # Extract headers and params - only pass if present
        get_kwargs = {}
        if "headers" in request_kwargs and request_kwargs["headers"]:
            get_kwargs["headers"] = request_kwargs["headers"]
        if "params" in request_kwargs and request_kwargs["params"]:
            get_kwargs["params"] = request_kwargs["params"]

        # Use client directly to maintain compatibility
        response = self.client.get(path, **get_kwargs)
        response.raise_for_status()
        return response.json()

    def create(self, resource: str, data: dict, **kwargs) -> dict:
        """
        Create a new resource via POST using operation resolution.

        Args:
            resource: The resource type (e.g., "zaak", "status")
            data: The data to POST
            **kwargs: Additional request kwargs (headers, request_kwargs, etc.)

        Returns:
            Response JSON with the created resource

        Examples:
            >>> crud.create("zaak", data={"zaaktype": "...", ...})
            >>> crud.create("zaak", data={...}, request_kwargs={"headers": {...}})
        """
        operation_id = f"{resource}_create"

        # Extract headers if provided
        request_kwargs = kwargs.get("request_kwargs", {})
        headers = request_kwargs.get("headers") or kwargs.get("headers")

        # Resolve the operation to get the correct path
        path, method = self.resolver.resolve_operation(operation_id, **kwargs)

        # Execute the request
        return self.executor.execute(method, path, data=data, headers=headers)

    def update(self, resource: str, data: dict, **kwargs) -> dict:
        """
        Update a resource via PUT.

        Args:
            resource: The resource type
            data: The complete updated data
            **kwargs: Additional parameters (url, uuid, request_kwargs, etc.)

        Returns:
            Response JSON with the updated resource

        Examples:
            >>> crud.update("zaak", data={...}, url="https://...")
            >>> crud.update("zaak", data={...}, uuid="123")
        """
        # Extract request_kwargs for headers
        request_kwargs = kwargs.pop("request_kwargs", {})

        if "url" in kwargs:
            # Normalize URL to path
            path = self.normalizer.normalize_to_path(kwargs["url"])
        else:
            # Use resource as-is (for backward compatibility)
            path = resource

        # Extract headers - only pass if present
        put_kwargs = {"json": data}
        if "headers" in request_kwargs and request_kwargs["headers"]:
            put_kwargs["headers"] = request_kwargs["headers"]

        # Use client directly for PUT
        response = self.client.put(path, **put_kwargs)
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

        Examples:
            >>> crud.partial_update("zaak", {"locked": True}, url="https://...")
            >>> crud.partial_update("document", url="https://...", locked=True)
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
                path, _ = self.resolver.resolve_operation(operation_id, **path_params)
            except (ValueError, KeyError):
                # Fallback to manual construction if schema resolution fails
                if zaak_uuid:
                    # Fallback: use pluralization for nested resources
                    plural_resource = self.pluralizer.pluralize(resource)
                    path = f"zaken/{zaak_uuid}/{plural_resource}"
                    if uuid:
                        path = f"{path}/{uuid}"
                else:
                    path = f"{resource}/{uuid}" if uuid else resource
        else:
            # Normalize URL to path
            path = self.normalizer.normalize_to_path(request_url)

        # Extract headers - only pass if present
        patch_kwargs = {"json": json_data}
        if "headers" in request_kwargs and request_kwargs["headers"]:
            patch_kwargs["headers"] = request_kwargs["headers"]

        # Make the PATCH request
        response = self.client.patch(path, **patch_kwargs)
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

        Examples:
            >>> crud.delete("zaak", uuid="12345678-...")
            >>> crud.delete("zaak", url="https://...")
        """
        if "url" in kwargs:
            path = self.normalizer.normalize_to_path(kwargs["url"])
        elif "uuid" in kwargs:
            path = f"{resource}/{kwargs['uuid']}"
        else:
            path = resource

        response = self.client.delete(path)
        response.raise_for_status()
        return None
