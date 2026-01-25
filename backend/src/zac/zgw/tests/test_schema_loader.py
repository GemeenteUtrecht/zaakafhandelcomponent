"""
Unit tests for SchemaLoader and SchemaRegistry.
"""

from unittest.mock import Mock, patch

from django.test import TestCase

from zac.zgw.schema.loader import SchemaLoader
from zac.zgw.schema.registry import SchemaRegistry


class SchemaLoaderTests(TestCase):
    """Tests for the SchemaLoader class."""

    def setUp(self):
        # Clear schema cache before each test
        SchemaRegistry.clear_cache()

    def test_init(self):
        """Test SchemaLoader initialization."""
        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        self.assertEqual(loader.base_url, "https://api.example.com")
        self.assertEqual(loader.service, service)

    def test_load_schema_no_service(self):
        """Test that load_schema returns None when no service is provided."""
        loader = SchemaLoader("https://api.example.com", service=None)
        result = loader.load_schema()

        self.assertIsNone(result)

    def test_is_test_environment(self):
        """Test test environment detection."""
        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        # We're running in unittest, so this should be True
        self.assertTrue(loader._is_test_environment())

    def test_resolve_schema_name_objecttypes(self):
        """Test schema name resolution for objecttypes API."""
        from zgw_consumers.constants import APITypes

        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        # URL pattern match
        result = loader._resolve_schema_name(
            APITypes.orc, "https://objecttype.example.com"
        )
        self.assertEqual(result, "objecttypes")

        result = loader._resolve_schema_name(
            APITypes.orc, "https://api.example.com/objecttypes"
        )
        self.assertEqual(result, "objecttypes")

    def test_resolve_schema_name_objects(self):
        """Test schema name resolution for objects API."""
        from zgw_consumers.constants import APITypes

        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        result = loader._resolve_schema_name(APITypes.orc, "https://object.example.com")
        self.assertEqual(result, "objects")

    def test_resolve_schema_name_standard_zgw(self):
        """Test schema name resolution for standard ZGW APIs."""
        from zgw_consumers.constants import APITypes

        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        # Standard ZGW APIs should use api_type directly
        result = loader._resolve_schema_name(APITypes.zrc, "https://zaken.example.com")
        self.assertEqual(result, APITypes.zrc)

        result = loader._resolve_schema_name(
            APITypes.ztc, "https://catalogi.example.com"
        )
        self.assertEqual(result, APITypes.ztc)

    def test_resolve_schema_name_kownsl(self):
        """Test schema name resolution for kownsl API."""
        from zgw_consumers.constants import APITypes

        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        result = loader._resolve_schema_name(APITypes.orc, "https://kownsl.example.com")
        self.assertEqual(result, "kownsl")

    def test_resolve_schema_name_kadaster(self):
        """Test schema name resolution for Kadaster/BAG API."""
        from zgw_consumers.constants import APITypes

        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        result = loader._resolve_schema_name(
            APITypes.orc, "https://kadaster.example.com"
        )
        self.assertEqual(result, "kadaster")

        result = loader._resolve_schema_name(APITypes.orc, "https://lvbag.example.com")
        self.assertEqual(result, "kadaster")

    def test_resolve_schema_name_brp(self):
        """Test schema name resolution for BRP API."""
        from zgw_consumers.constants import APITypes

        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        result = loader._resolve_schema_name(APITypes.orc, "https://brp.example.com")
        self.assertEqual(result, "brp")

    def test_resolve_schema_name_dowc(self):
        """Test schema name resolution for DOWC API."""
        from zgw_consumers.constants import APITypes

        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        result = loader._resolve_schema_name(APITypes.orc, "https://dowc.example.com")
        self.assertEqual(result, "dowc")

    def test_resolve_schema_name_unknown_orc(self):
        """Test schema name resolution for unknown ORC API returns None."""
        from zgw_consumers.constants import APITypes

        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        result = loader._resolve_schema_name(
            APITypes.orc, "https://unknown.example.com"
        )
        self.assertIsNone(result)

    def test_resolve_production_schema_url_bag(self):
        """Test production schema URL resolution for BAG API."""
        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        mock_settings = Mock()
        mock_settings.EXTERNAL_API_SCHEMAS = {"BAG_API_SCHEMA": "https://schema.bag"}

        result = loader._resolve_production_schema_url(
            "https://kadaster.example.com", mock_settings
        )
        self.assertEqual(result, "https://schema.bag")

        result = loader._resolve_production_schema_url(
            "https://lvbag.example.com", mock_settings
        )
        self.assertEqual(result, "https://schema.bag")

    def test_resolve_production_schema_url_kownsl(self):
        """Test production schema URL resolution for Kownsl API."""
        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        mock_settings = Mock()
        mock_settings.EXTERNAL_API_SCHEMAS = {
            "KOWNSL_API_SCHEMA": "https://schema.kownsl"
        }

        result = loader._resolve_production_schema_url(
            "https://kownsl.example.com", mock_settings
        )
        self.assertEqual(result, "https://schema.kownsl")

    def test_resolve_production_schema_url_unknown(self):
        """Test production schema URL resolution for unknown API returns None."""
        service = Mock()
        loader = SchemaLoader("https://api.example.com", service)

        mock_settings = Mock()
        mock_settings.EXTERNAL_API_SCHEMAS = {}

        result = loader._resolve_production_schema_url(
            "https://unknown.example.com", mock_settings
        )
        self.assertIsNone(result)


class SchemaRegistryTests(TestCase):
    """Tests for the SchemaRegistry class."""

    def setUp(self):
        # Clear schema cache before each test
        SchemaRegistry.clear_cache()

    def test_get_schema_not_cached(self):
        """Test getting schema when not cached calls loader."""
        mock_loader = Mock()
        mock_loader.load_schema.return_value = {"openapi": "3.0.0"}

        result = SchemaRegistry.get_schema("https://api.example.com", mock_loader)

        self.assertEqual(result, {"openapi": "3.0.0"})
        mock_loader.load_schema.assert_called_once()

    def test_get_schema_cached(self):
        """Test getting schema when cached doesn't call loader again."""
        mock_loader = Mock()
        mock_loader.load_schema.return_value = {"openapi": "3.0.0"}

        # First call loads and caches
        result1 = SchemaRegistry.get_schema("https://api.example.com", mock_loader)
        self.assertEqual(result1, {"openapi": "3.0.0"})
        self.assertEqual(mock_loader.load_schema.call_count, 1)

        # Second call uses cache
        result2 = SchemaRegistry.get_schema("https://api.example.com", mock_loader)
        self.assertEqual(result2, {"openapi": "3.0.0"})
        self.assertEqual(mock_loader.load_schema.call_count, 1)  # Not called again

    def test_get_schema_none_is_cached(self):
        """Test that None results are also cached to avoid repeated attempts."""
        mock_loader = Mock()
        mock_loader.load_schema.return_value = None

        # First call
        result1 = SchemaRegistry.get_schema("https://api.example.com", mock_loader)
        self.assertIsNone(result1)
        self.assertEqual(mock_loader.load_schema.call_count, 1)

        # Second call should use cached None
        result2 = SchemaRegistry.get_schema("https://api.example.com", mock_loader)
        self.assertIsNone(result2)
        self.assertEqual(mock_loader.load_schema.call_count, 1)  # Not called again

    def test_clear_cache_specific_url(self):
        """Test clearing cache for specific URL."""
        mock_loader = Mock()
        mock_loader.load_schema.return_value = {"openapi": "3.0.0"}

        # Cache two schemas
        SchemaRegistry.get_schema("https://api1.example.com", mock_loader)
        SchemaRegistry.get_schema("https://api2.example.com", mock_loader)

        # Clear one
        SchemaRegistry.clear_cache("https://api1.example.com")

        # First should be gone, second should remain
        self.assertFalse(SchemaRegistry.has_schema("https://api1.example.com"))
        self.assertTrue(SchemaRegistry.has_schema("https://api2.example.com"))

    def test_clear_cache_all(self):
        """Test clearing all cached schemas."""
        mock_loader = Mock()
        mock_loader.load_schema.return_value = {"openapi": "3.0.0"}

        # Cache two schemas
        SchemaRegistry.get_schema("https://api1.example.com", mock_loader)
        SchemaRegistry.get_schema("https://api2.example.com", mock_loader)

        # Clear all
        SchemaRegistry.clear_cache()

        # Both should be gone
        self.assertFalse(SchemaRegistry.has_schema("https://api1.example.com"))
        self.assertFalse(SchemaRegistry.has_schema("https://api2.example.com"))
        self.assertEqual(SchemaRegistry.get_cached_urls(), [])

    def test_has_schema(self):
        """Test checking if schema is cached."""
        self.assertFalse(SchemaRegistry.has_schema("https://api.example.com"))

        mock_loader = Mock()
        mock_loader.load_schema.return_value = {"openapi": "3.0.0"}
        SchemaRegistry.get_schema("https://api.example.com", mock_loader)

        self.assertTrue(SchemaRegistry.has_schema("https://api.example.com"))

    def test_get_cached_urls(self):
        """Test getting list of cached URLs."""
        mock_loader = Mock()
        mock_loader.load_schema.return_value = {"openapi": "3.0.0"}

        SchemaRegistry.get_schema("https://api1.example.com", mock_loader)
        SchemaRegistry.get_schema("https://api2.example.com", mock_loader)

        urls = SchemaRegistry.get_cached_urls()
        self.assertEqual(len(urls), 2)
        self.assertIn("https://api1.example.com", urls)
        self.assertIn("https://api2.example.com", urls)
