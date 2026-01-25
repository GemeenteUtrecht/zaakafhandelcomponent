"""
Operation resolution utilities for ZGW API client.

This module provides utilities for resolving operation IDs to URL paths and HTTP methods,
using either OAS schema lookup or pattern-based inference.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pluralization import PluralizationService


class OperationResolver:
    """
    Resolver for OAS operation IDs to URL paths and HTTP methods.

    This class handles operation resolution using two strategies:
    1. Schema-based: Look up operation ID in OAS schema (most accurate)
    2. Inference-based: Infer from operation ID pattern when schema unavailable

    The resolver uses Dutch pluralization rules for resource names.
    """

    def __init__(self, schema: dict | None, pluralizer: "PluralizationService"):
        """
        Initialize the operation resolver.

        Args:
            schema: Parsed OAS schema dict (or None if unavailable)
            pluralizer: PluralizationService for resource name pluralization
        """
        self.schema = schema
        self.pluralizer = pluralizer

    def resolve_operation(self, operation_id: str, **path_params) -> tuple[str, str]:
        """
        Resolve an operation ID to a URL path and HTTP method.

        Uses schema-based lookup if available, otherwise falls back to inference.

        Args:
            operation_id: The OAS operation ID (e.g., "catalogus_list", "zaak_create")
            **path_params: Parameters to substitute in the path (e.g., uuid="123")

        Returns:
            Tuple of (path, method)
            - path: Relative path without leading slash (e.g., "zaken/123")
            - method: HTTP method in uppercase (e.g., "GET", "POST")

        Raises:
            ValueError: If operation cannot be resolved

        Examples:
            >>> resolver = OperationResolver(schema, pluralizer)
            >>> path, method = resolver.resolve_operation("zaak_list")
            >>> path, method
            ('zaken', 'GET')
            >>> path, method = resolver.resolve_operation("zaak_read", uuid="123")
            >>> path, method
            ('zaken/123', 'GET')
        """
        if self.schema and "paths" in self.schema:
            try:
                return self._resolve_from_schema(operation_id, **path_params)
            except ValueError:
                # Schema lookup failed, fall back to inference
                pass

        # No schema or not found in schema - infer from operation_id
        return self._infer_operation(operation_id, **path_params)

    def _resolve_from_schema(self, operation_id: str, **path_params) -> tuple[str, str]:
        """
        Resolve operation ID using OAS schema lookup.

        Searches the schema's paths for a matching operationId.

        Args:
            operation_id: The OAS operation ID
            **path_params: Parameters to substitute in the path

        Returns:
            Tuple of (path, method)

        Raises:
            ValueError: If operation ID not found in schema
        """
        # Search for the operation in the schema
        for path, path_item in self.schema["paths"].items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "patch", "delete"]:
                    if operation.get("operationId") == operation_id:
                        # Substitute path parameters
                        resolved_path = path
                        for key, value in path_params.items():
                            resolved_path = resolved_path.replace(
                                f"{{{key}}}", str(value)
                            )
                        return resolved_path.lstrip("/"), method.upper()

        raise ValueError(f"Operation ID not found in schema: {operation_id}")

    def _infer_operation(self, operation_id: str, **path_params) -> tuple[str, str]:
        """
        Infer URL and method from operation_id when schema is not available.

        Uses common ZGW API patterns:
        - {resource}_list -> GET /{resources}
        - {resource}_read -> GET /{resources}/{uuid}
        - {resource}_retrieve -> GET /{resources}/{uuid}
        - {resource}_create -> POST /{resources}
        - {resource}_update -> PUT /{resources}/{uuid}
        - {resource}_partial_update -> PATCH /{resources}/{uuid}
        - {resource}_delete -> DELETE /{resources}/{uuid}

        Args:
            operation_id: The operation ID to parse
            **path_params: Parameters to substitute (e.g., uuid="123")

        Returns:
            Tuple of (path, method)

        Raises:
            ValueError: If operation ID doesn't match expected pattern

        Examples:
            >>> resolver = OperationResolver(None, pluralizer)
            >>> resolver._infer_operation("zaak_list")
            ('zaken', 'GET')
            >>> resolver._infer_operation("zaak_read", uuid="123")
            ('zaken/123', 'GET')
        """
        # Known actions (ordered by length descending to match longest first)
        known_actions = [
            "partial_update",
            "retrieve",
            "create",
            "update",
            "delete",
            "list",
            "read",
        ]

        # Find the action suffix
        resource = None
        action = None
        for known_action in known_actions:
            if operation_id.endswith(f"_{known_action}"):
                action = known_action
                resource = operation_id[: -(len(action) + 1)]  # Remove _{action}
                break

        if not resource or not action:
            raise ValueError(f"Cannot infer URL from operation_id: {operation_id}")

        # Apply pluralization rules for Dutch ZGW APIs
        resource_plural = self.pluralizer.pluralize(resource)

        # Method and path template mapping
        # Use placeholder {uuid} for templates that need a UUID
        method_map = {
            "list": ("GET", f"{resource_plural}"),
            "read": ("GET", f"{resource_plural}/{{uuid}}"),
            "retrieve": ("GET", f"{resource_plural}/{{uuid}}"),
            "create": ("POST", f"{resource_plural}"),
            "update": ("PUT", f"{resource_plural}/{{uuid}}"),
            "partial_update": ("PATCH", f"{resource_plural}/{{uuid}}"),
            "delete": ("DELETE", f"{resource_plural}/{{uuid}}"),
        }

        if action not in method_map:
            raise ValueError(f"Unknown action in operation_id: {action}")

        method, path_template = method_map[action]

        # Substitute parameters
        path = path_template
        for key, value in path_params.items():
            path = path.replace(f"{{{key}}}", str(value))

        return path, method

    def supports_operation(self, operation_id: str) -> bool:
        """
        Check if an operation ID can be resolved.

        Args:
            operation_id: The operation ID to check

        Returns:
            True if operation can be resolved, False otherwise

        Examples:
            >>> resolver = OperationResolver(schema, pluralizer)
            >>> resolver.supports_operation("zaak_list")
            True
            >>> resolver.supports_operation("invalid")
            False
        """
        try:
            self.resolve_operation(operation_id)
            return True
        except ValueError:
            return False
