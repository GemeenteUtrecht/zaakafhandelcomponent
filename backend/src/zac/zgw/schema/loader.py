"""
OAS schema loading utilities for ZGW API client.

This module provides utilities for loading OpenAPI Specification (OAS) schemas
from test files or production URLs.
"""

import logging
import sys

import requests
import yaml
from zgw_consumers.models import Service

logger = logging.getLogger(__name__)


class SchemaLoader:
    """
    Loader for OAS schemas from test files or production endpoints.

    This class handles loading schemas differently in test vs production environments:
    - In tests: Load from local test schema files (no network calls)
    - In production: Fetch from remote URLs configured in settings

    The loader performs schema name resolution based on API type and API root URL patterns.
    """

    def __init__(self, base_url: str, service: Service = None):
        """
        Initialize the schema loader.

        Args:
            base_url: The base URL of the API
            service: Optional Service model instance for schema resolution
        """
        self.base_url = base_url
        self.service = service

    def load_schema(self) -> dict | None:
        """
        Load OAS schema from test files or production URLs.

        Returns:
            Parsed OAS schema dict, or None if not available

        The loading strategy:
        1. Test environment: Load from zgw_consumers_oas test schema files
        2. Production: Fetch from URLs configured in EXTERNAL_API_SCHEMAS
        3. Fallback: Return None (client will use pluralization inference)
        """
        if not self.service:
            return None

        if self._is_test_environment():
            return self._load_test_schema()
        return self._load_production_schema()

    def _is_test_environment(self) -> bool:
        """
        Detect if we're in a test environment.

        Returns:
            True if running in test context, False otherwise
        """
        return (
            "pytest" in sys.modules
            or "unittest" in sys.modules
            or hasattr(sys, "_called_from_test")
        )

    def _load_test_schema(self) -> dict | None:
        """
        Load schema from test schema files.

        Uses zgw_consumers_oas.read_schema() to load schemas from the
        test fixtures directory without making network calls.

        Returns:
            Parsed OAS schema dict, or None if not found
        """
        try:
            from zgw_consumers.constants import APITypes
            from zgw_consumers_oas import read_schema

            api_type = getattr(self.service, "api_type", None)
            api_root = getattr(self.service, "api_root", "").lower()

            schema_name = self._resolve_schema_name(api_type, api_root)

            if not schema_name:
                return None

            schema_bytes = read_schema(schema_name)
            return yaml.safe_load(schema_bytes)

        except Exception as e:
            logger.debug(f"Could not load test OAS schema for {self.service}: {e}")
            return None

    def _load_production_schema(self) -> dict | None:
        """
        Load schema from production URLs.

        Fetches schemas from URLs configured in Django settings.EXTERNAL_API_SCHEMAS.

        Returns:
            Parsed OAS schema dict, or None if not configured or fetch failed
        """
        try:
            from django.conf import settings

            api_root = getattr(self.service, "api_root", "").lower()
            schema_url = self._resolve_production_schema_url(api_root, settings)

            if not schema_url:
                logger.debug(
                    f"No EXTERNAL_API_SCHEMA configured for service with api_root: {api_root}"
                )
                return None

            logger.debug(f"Fetching OAS schema from {schema_url}")
            response = requests.get(schema_url, timeout=10)
            response.raise_for_status()

            if schema_url.endswith(".json"):
                return response.json()
            return yaml.safe_load(response.content)

        except Exception as e:
            logger.warning(
                f"Could not load production OAS schema for {self.service}: {e}"
            )
            return None

    def _resolve_schema_name(self, api_type: str, api_root: str) -> str | None:
        """
        Resolve schema name based on API type and API root URL.

        URL patterns are checked first (handles non-standard APIs and misconfigurations).
        If no pattern matches, uses api_type directly for standard ZGW APIs.

        Args:
            api_type: The API type from Service model (e.g., APITypes.zrc)
            api_root: The API root URL (lowercased)

        Returns:
            Schema name for read_schema(), or None if cannot determine
        """
        from zgw_consumers.constants import APITypes

        # Check URL patterns first (handles edge cases and non-standard APIs)
        # Order matters: more specific patterns first
        if "objecttype" in api_root:
            # Covers both objecttype.nl and objecttypes in path
            return "objecttypes"
        elif "object" in api_root:
            # Must come after objecttype check
            return "objects"
        elif "kownsl" in api_root:
            return "kownsl"
        elif "kadaster" in api_root or "lvbag" in api_root:
            return "kadaster"
        elif "brp" in api_root:
            return "brp"
        elif "dowc" in api_root:
            return "dowc"
        elif "zac" in api_root:
            return "zac"

        # If no URL pattern matched, use api_type directly for standard ZGW APIs
        if api_type == APITypes.orc:
            # Unknown orc-type API, can't determine schema
            logger.debug(
                f"Cannot infer schema name for APITypes.orc service with api_root: {api_root}"
            )
            return None

        # Use api_type as schema name (standard ZGW APIs like zrc, ztc, drc)
        return api_type

    def _resolve_production_schema_url(self, api_root: str, settings) -> str | None:
        """
        Resolve production schema URL from Django settings.

        Maps API root URL patterns to schema URLs in EXTERNAL_API_SCHEMAS setting.

        Args:
            api_root: The API root URL (lowercased)
            settings: Django settings module

        Returns:
            Schema URL, or None if not configured
        """
        # Map service URL patterns to schema URLs
        # Order matters: more specific patterns first
        if "kadaster" in api_root or "lvbag" in api_root or "bag" in api_root:
            return settings.EXTERNAL_API_SCHEMAS.get("BAG_API_SCHEMA")
        elif "kownsl" in api_root:
            return settings.EXTERNAL_API_SCHEMAS.get("KOWNSL_API_SCHEMA")
        elif "objecttype" in api_root:
            return settings.EXTERNAL_API_SCHEMAS.get("OBJECTTYPES_API_SCHEMA")
        elif "object" in api_root:
            return settings.EXTERNAL_API_SCHEMAS.get("OBJECTS_API_SCHEMA")
        elif "dowc" in api_root:
            return settings.EXTERNAL_API_SCHEMAS.get("DOWC_API_SCHEMA")
        elif "zaken" in api_root or "zrc" in api_root:
            return settings.EXTERNAL_API_SCHEMAS.get("ZRC_API_SCHEMA")

        return None
