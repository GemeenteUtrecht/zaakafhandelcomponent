"""
Modern ZGW API Client built on composition.

This module provides a lightweight ZGWClient that composes specialized components
for schema loading, operation resolution, URL normalization, and CRUD operations.
"""

from typing import Any

from ape_pie import APIClient
from zgw_consumers.models import Service

from .compat.legacy import BackwardCompatibilityMixin
from .operations.executor import OperationExecutor
from .operations.pluralization import PluralizationService
from .operations.resolver import OperationResolver
from .resources.crud import ResourceCRUD
from .schema.loader import SchemaLoader
from .schema.registry import SchemaRegistry
from .utils.errors import ErrorHandler
from .utils.url_normalizer import URLNormalizer


class ZGWClient(BackwardCompatibilityMixin, APIClient):
    """
    Modern ZGW API client built on composition.

    This client provides:
    - Full ape_pie.APIClient functionality (Session-based requests with base URL)
    - Modular architecture with pluggable components
    - API convenience methods for ZGW resources (create, retrieve, list, etc.)
    - Backward compatibility with zgw-consumers <1.0 (via mixin)

    Architecture:
    - SchemaLoader: Load OAS schemas from test files or production URLs
    - SchemaRegistry: Cache schemas globally
    - OperationResolver: Resolve operation IDs to (path, method) tuples
    - OperationExecutor: Execute HTTP requests with error handling
    - URLNormalizer: Normalize URLs and paths
    - PluralizationService: Handle Dutch resource name pluralization
    - ResourceCRUD: High-level CRUD operations
    - ErrorHandler: Convert HTTPError to ClientError

    Usage:
        from zgw_consumers.models import Service
        from zgw_consumers.client import build_client
        from zac.zgw import ZGWClient

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
            service: Optional Service model instance for schema loading
            **kwargs: Additional kwargs (e.g., nlx_base_url for NLX support)
        """
        super().__init__(base_url, request_kwargs, **kwargs)
        self.service = service

        # Initialize components
        self._schema_loader = SchemaLoader(base_url, service)
        self._schema_registry = SchemaRegistry()
        self._pluralizer = PluralizationService()
        self._url_normalizer = URLNormalizer(base_url)
        self._error_handler = ErrorHandler()

        # Lazy-initialized components (depend on schema)
        self._resolver = None
        self._executor = None
        self._crud = None

    @property
    def schema(self) -> dict | None:
        """
        Lazy-load and cache the OAS schema for this service.

        Returns:
            Parsed OAS schema dict, or None if not available
        """
        return self._schema_registry.get_schema(self.base_url, self._schema_loader)

    def _get_resolver(self) -> OperationResolver:
        """Get or create the OperationResolver."""
        if self._resolver is None:
            self._resolver = OperationResolver(self.schema, self._pluralizer)
        return self._resolver

    def _get_executor(self) -> OperationExecutor:
        """Get or create the OperationExecutor."""
        if self._executor is None:
            self._executor = OperationExecutor(self, self._error_handler)
        return self._executor

    def _get_crud(self) -> ResourceCRUD:
        """Get or create the ResourceCRUD."""
        if self._crud is None:
            self._crud = ResourceCRUD(
                self,
                self._get_resolver(),
                self._get_executor(),
                self._url_normalizer,
                self._pluralizer,
            )
        return self._crud

    def request(self, method: str, url: str, *args, **kwargs):
        """
        Make HTTP request using the parent APIClient.

        Calls pre_request hook before delegating to parent (for backward compatibility).

        Args:
            method: HTTP method
            url: Request URL
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            requests.Response object
        """
        kwargs = self.pre_request(method, url, **kwargs)
        return super().request(method, url, *args, **kwargs)

    def operation(self, operation_id: str, **kwargs):
        """
        Execute an operation by its operation ID.

        This resolves the operation ID to a (path, method) tuple using the OAS schema
        or inference, then executes the HTTP request.

        Args:
            operation_id: The OAS operation ID (e.g., "zaak_list", "document_lock")
            **kwargs: Operation parameters (data, params, headers, url, uuid, etc.)

        Returns:
            Response data (parsed JSON)

        Examples:
            >>> client.operation("zaak_list", params={"status": "open"})
            >>> client.operation("document_lock", data={}, url="https://...")
        """
        # Extract parameters
        data = kwargs.pop("data", None)
        params = kwargs.pop("params", None)
        headers = kwargs.pop("headers", None)
        explicit_url = kwargs.pop("url", None)

        # If explicit URL provided, normalize it to a path
        if explicit_url:
            path, query_params = self._url_normalizer.extract_query_params(explicit_url)
            # Merge extracted query params with provided params
            if query_params:
                if params is None:
                    params = {}
                params = {**query_params, **params}

            # Try to determine method from operation_id or default to GET
            try:
                _, method = self._get_resolver().resolve_operation(
                    operation_id, **kwargs
                )
            except ValueError:
                # If operation resolution fails, default to POST if data else GET
                method = "POST" if data is not None else "GET"
        else:
            # Use operation resolution to get path and method
            path, method = self._get_resolver().resolve_operation(
                operation_id, **kwargs
            )

        # Execute the operation
        return self._get_executor().execute(
            method, path, data=data, params=params, headers=headers
        )

    # CRUD convenience methods - delegate to ResourceCRUD

    def list(self, resource: str, query_params: dict | None = None, **kwargs) -> dict:
        """
        List resources from the API.

        Args:
            resource: The resource type (e.g., "zaak", "catalogus")
            query_params: Optional query parameters
            **kwargs: Additional request kwargs

        Returns:
            Response JSON (usually contains 'results' key)

        Examples:
            >>> client.list("catalogus", query_params={"domein": "ABR"})
            >>> client.list("zaak", query_params={"status": "open"})
        """
        return self._get_crud().list(resource, query_params, **kwargs)

    def retrieve(self, resource: str, url: str | None = None, **kwargs) -> dict:
        """
        Retrieve a single resource.

        Args:
            resource: The resource type (e.g., "zaak", "document")
            url: Optional full URL to the resource
            **kwargs: Additional parameters (uuid, request_kwargs, etc.)

        Returns:
            Response JSON

        Examples:
            >>> client.retrieve("zaak", url="https://zaken.nl/api/v1/zaken/123")
            >>> client.retrieve("zaak", uuid="12345678-...")
        """
        return self._get_crud().retrieve(resource, url, **kwargs)

    def create(self, resource: str, data: dict, **kwargs) -> dict:
        """
        Create a new resource via POST.

        Args:
            resource: The resource type (e.g., "zaak", "status")
            data: The data to POST
            **kwargs: Additional request kwargs

        Returns:
            Response JSON with the created resource

        Examples:
            >>> client.create("zaak", data={"zaaktype": "...", ...})
        """
        return self._get_crud().create(resource, data, **kwargs)

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
            >>> client.update("zaak", data={...}, url="https://...")
        """
        return self._get_crud().update(resource, data, **kwargs)

    def partial_update(self, resource: str, data: dict | None = None, **kwargs) -> dict:
        """
        Partially update a resource via PATCH.

        Args:
            resource: The resource type
            data: Optional dict of fields to update
            **kwargs: Fields to update, plus url or uuid

        Returns:
            Response JSON with the updated resource

        Examples:
            >>> client.partial_update("zaak", {"locked": True}, url="https://...")
            >>> client.partial_update("document", url="https://...", locked=True)
        """
        return self._get_crud().partial_update(resource, data, **kwargs)

    def delete(self, resource: str, **kwargs) -> None:
        """
        Delete a resource.

        Args:
            resource: The resource type
            **kwargs: Additional parameters (url, uuid, etc.)

        Returns:
            None

        Examples:
            >>> client.delete("zaak", uuid="12345678-...")
        """
        return self._get_crud().delete(resource, **kwargs)
