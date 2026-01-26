"""
Schema caching registry for ZGW API clients.

This module provides a centralized registry for caching OAS schemas to avoid
repeated loading from files or network endpoints.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .loader import SchemaLoader


class SchemaRegistry:
    """
    Registry for caching loaded OAS schemas.

    This class maintains a global cache of schemas keyed by base URL.
    Schemas are loaded once and reused across all clients for the same API.

    Class attributes are used for global caching across all ZGWClient instances.
    """

    # Global schema cache: {base_url: schema_dict}
    _schemas: dict[str, dict] = {}

    @classmethod
    def get_schema(cls, base_url: str, loader: "SchemaLoader") -> dict | None:
        """
        Get schema from cache or load it using the provided loader.

        Args:
            base_url: The base URL of the API (cache key)
            loader: SchemaLoader instance to use if schema not cached

        Returns:
            Parsed OAS schema dict, or None if not available

        Examples:
            >>> from zac.zgw.schema.loader import SchemaLoader
            >>> loader = SchemaLoader("https://api.example.com", service)
            >>> schema = SchemaRegistry.get_schema("https://api.example.com", loader)
        """
        # Check cache first
        if base_url in cls._schemas:
            return cls._schemas[base_url]

        # Load schema using provided loader
        schema = loader.load_schema()

        # Cache the result (even if None, to avoid repeated load attempts)
        cls._schemas[base_url] = schema

        return schema

    @classmethod
    def clear_cache(cls, base_url: str = None):
        """
        Clear cached schemas.

        Args:
            base_url: If provided, clear only this URL's schema.
                     If None, clear all cached schemas.

        Examples:
            >>> # Clear specific schema
            >>> SchemaRegistry.clear_cache("https://api.example.com")
            >>>
            >>> # Clear all schemas
            >>> SchemaRegistry.clear_cache()
        """
        if base_url:
            # Clear specific URL
            cls._schemas.pop(base_url, None)
        else:
            # Clear all schemas
            cls._schemas.clear()

    @classmethod
    def has_schema(cls, base_url: str) -> bool:
        """
        Check if a schema is cached for the given base URL.

        Args:
            base_url: The base URL to check

        Returns:
            True if schema is cached, False otherwise

        Examples:
            >>> SchemaRegistry.has_schema("https://api.example.com")
            False
        """
        return base_url in cls._schemas

    @classmethod
    def get_cached_urls(cls) -> list[str]:
        """
        Get list of all base URLs with cached schemas.

        Returns:
            List of base URLs

        Examples:
            >>> SchemaRegistry.get_cached_urls()
            ['https://api.example.com', 'https://other.api.com']
        """
        return list(cls._schemas.keys())
