"""
Unit tests for OperationResolver.
"""

from django.test import TestCase

from zac.zgw.operations.pluralization import PluralizationService
from zac.zgw.operations.resolver import OperationResolver


class OperationResolverTests(TestCase):
    """Tests for the OperationResolver class."""

    def setUp(self):
        self.pluralizer = PluralizationService()

    def test_init(self):
        """Test OperationResolver initialization."""
        schema = {"openapi": "3.0.0"}
        resolver = OperationResolver(schema, self.pluralizer)

        self.assertEqual(resolver.schema, schema)
        self.assertEqual(resolver.pluralizer, self.pluralizer)

    def test_infer_operation_list(self):
        """Test inferring list operation."""
        resolver = OperationResolver(None, self.pluralizer)

        path, method = resolver._infer_operation("zaak_list")

        self.assertEqual(path, "zaken")
        self.assertEqual(method, "GET")

    def test_infer_operation_read(self):
        """Test inferring read operation with UUID."""
        resolver = OperationResolver(None, self.pluralizer)

        path, method = resolver._infer_operation("zaak_read", uuid="123")

        self.assertEqual(path, "zaken/123")
        self.assertEqual(method, "GET")

    def test_infer_operation_retrieve(self):
        """Test inferring retrieve operation (alias for read)."""
        resolver = OperationResolver(None, self.pluralizer)

        path, method = resolver._infer_operation("zaak_retrieve", uuid="456")

        self.assertEqual(path, "zaken/456")
        self.assertEqual(method, "GET")

    def test_infer_operation_create(self):
        """Test inferring create operation."""
        resolver = OperationResolver(None, self.pluralizer)

        path, method = resolver._infer_operation("zaak_create")

        self.assertEqual(path, "zaken")
        self.assertEqual(method, "POST")

    def test_infer_operation_update(self):
        """Test inferring update operation."""
        resolver = OperationResolver(None, self.pluralizer)

        path, method = resolver._infer_operation("zaak_update", uuid="789")

        self.assertEqual(path, "zaken/789")
        self.assertEqual(method, "PUT")

    def test_infer_operation_partial_update(self):
        """Test inferring partial_update operation."""
        resolver = OperationResolver(None, self.pluralizer)

        path, method = resolver._infer_operation("zaak_partial_update", uuid="abc")

        self.assertEqual(path, "zaken/abc")
        self.assertEqual(method, "PATCH")

    def test_infer_operation_delete(self):
        """Test inferring delete operation."""
        resolver = OperationResolver(None, self.pluralizer)

        path, method = resolver._infer_operation("zaak_delete", uuid="def")

        self.assertEqual(path, "zaken/def")
        self.assertEqual(method, "DELETE")

    def test_infer_operation_invalid_format(self):
        """Test that invalid operation ID format raises ValueError."""
        resolver = OperationResolver(None, self.pluralizer)

        with self.assertRaises(ValueError) as context:
            resolver._infer_operation("invalidformat")

        self.assertIn("Cannot infer URL", str(context.exception))

    def test_infer_operation_unknown_action(self):
        """Test that unknown action raises ValueError."""
        resolver = OperationResolver(None, self.pluralizer)

        with self.assertRaises(ValueError) as context:
            resolver._infer_operation("zaak_unknown")

        self.assertIn("Cannot infer URL", str(context.exception))

    def test_infer_operation_uses_pluralization(self):
        """Test that inference uses pluralization service."""
        resolver = OperationResolver(None, self.pluralizer)

        # Test with catalogus -> catalogussen
        path, method = resolver._infer_operation("catalogus_list")

        self.assertEqual(path, "catalogussen")
        self.assertEqual(method, "GET")

    def test_resolve_from_schema(self):
        """Test resolving operation from schema."""
        schema = {
            "paths": {
                "/zaken": {
                    "get": {"operationId": "zaak_list"},
                    "post": {"operationId": "zaak_create"},
                },
                "/zaken/{uuid}": {
                    "get": {"operationId": "zaak_read"},
                    "put": {"operationId": "zaak_update"},
                    "patch": {"operationId": "zaak_partial_update"},
                    "delete": {"operationId": "zaak_delete"},
                },
            }
        }

        resolver = OperationResolver(schema, self.pluralizer)

        # Test list
        path, method = resolver._resolve_from_schema("zaak_list")
        self.assertEqual(path, "zaken")
        self.assertEqual(method, "GET")

        # Test read with UUID
        path, method = resolver._resolve_from_schema("zaak_read", uuid="123")
        self.assertEqual(path, "zaken/123")
        self.assertEqual(method, "GET")

        # Test create
        path, method = resolver._resolve_from_schema("zaak_create")
        self.assertEqual(path, "zaken")
        self.assertEqual(method, "POST")

    def test_resolve_from_schema_not_found(self):
        """Test that missing operation in schema raises ValueError."""
        schema = {"paths": {}}

        resolver = OperationResolver(schema, self.pluralizer)

        with self.assertRaises(ValueError) as context:
            resolver._resolve_from_schema("zaak_list")

        self.assertIn("not found in schema", str(context.exception))

    def test_resolve_operation_uses_schema_when_available(self):
        """Test that resolve_operation prefers schema over inference."""
        schema = {
            "paths": {
                "/custom-path": {
                    "get": {"operationId": "zaak_list"},
                },
            }
        }

        resolver = OperationResolver(schema, self.pluralizer)

        path, method = resolver.resolve_operation("zaak_list")

        # Should use schema path, not inferred path
        self.assertEqual(path, "custom-path")
        self.assertEqual(method, "GET")

    def test_resolve_operation_falls_back_to_inference(self):
        """Test that resolve_operation falls back to inference if not in schema."""
        schema = {"paths": {}}  # Empty schema

        resolver = OperationResolver(schema, self.pluralizer)

        path, method = resolver.resolve_operation("zaak_list")

        # Should use inference
        self.assertEqual(path, "zaken")
        self.assertEqual(method, "GET")

    def test_resolve_operation_no_schema(self):
        """Test that resolve_operation works without schema."""
        resolver = OperationResolver(None, self.pluralizer)

        path, method = resolver.resolve_operation("zaak_list")

        self.assertEqual(path, "zaken")
        self.assertEqual(method, "GET")

    def test_supports_operation_true(self):
        """Test supports_operation returns True for valid operations."""
        resolver = OperationResolver(None, self.pluralizer)

        self.assertTrue(resolver.supports_operation("zaak_list"))
        self.assertTrue(resolver.supports_operation("zaak_read"))
        self.assertTrue(resolver.supports_operation("catalogus_create"))

    def test_supports_operation_false(self):
        """Test supports_operation returns False for invalid operations."""
        resolver = OperationResolver(None, self.pluralizer)

        self.assertFalse(resolver.supports_operation("invalid"))
        self.assertFalse(resolver.supports_operation("zaak_unknown"))
