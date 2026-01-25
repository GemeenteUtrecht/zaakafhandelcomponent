"""
Unit tests for URLNormalizer.
"""

from django.test import TestCase

from zac.zgw.utils.url_normalizer import URLNormalizer


class URLNormalizerTests(TestCase):
    """Tests for the URLNormalizer class."""

    def test_init(self):
        """Test URLNormalizer initialization."""
        normalizer = URLNormalizer("https://api.example.com/api/v1")

        self.assertEqual(normalizer.base_url, "https://api.example.com/api/v1")
        self.assertEqual(normalizer.base_path, "api/v1")

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base_url."""
        normalizer = URLNormalizer("https://api.example.com/api/v1/")

        self.assertEqual(normalizer.base_url, "https://api.example.com/api/v1")

    def test_is_full_url(self):
        """Test full URL detection."""
        normalizer = URLNormalizer("https://api.example.com")

        self.assertTrue(normalizer.is_full_url("https://api.example.com/zaken"))
        self.assertTrue(normalizer.is_full_url("http://api.example.com/zaken"))
        self.assertFalse(normalizer.is_full_url("zaken/123"))
        self.assertFalse(normalizer.is_full_url("/api/v1/zaken"))

    def test_normalize_to_path_full_url_matching_base(self):
        """Test normalizing full URL that matches base URL."""
        normalizer = URLNormalizer("https://api.example.com/api/v1")

        result = normalizer.normalize_to_path(
            "https://api.example.com/api/v1/zaken/123"
        )
        self.assertEqual(result, "zaken/123")

    def test_normalize_to_path_full_url_different_base(self):
        """Test normalizing full URL with different base."""
        normalizer = URLNormalizer("https://api.example.com/api/v1")

        result = normalizer.normalize_to_path("https://other.com/api/v2/zaken/123")
        self.assertEqual(result, "api/v2/zaken/123")

    def test_normalize_to_path_relative_path(self):
        """Test normalizing relative path."""
        normalizer = URLNormalizer("https://api.example.com/api/v1")

        result = normalizer.normalize_to_path("zaken/123")
        self.assertEqual(result, "zaken/123")

        result = normalizer.normalize_to_path("/zaken/123")
        self.assertEqual(result, "zaken/123")

    def test_normalize_to_path_with_base_path(self):
        """Test normalizing path that includes base path."""
        normalizer = URLNormalizer("https://api.example.com/api/v1")

        result = normalizer.normalize_to_path("/api/v1/zaken/123")
        self.assertEqual(result, "zaken/123")

        result = normalizer.normalize_to_path("api/v1/zaken/123")
        self.assertEqual(result, "zaken/123")

    def test_normalize_to_path_strips_query_params(self):
        """Test that query parameters are stripped."""
        normalizer = URLNormalizer("https://api.example.com")

        result = normalizer.normalize_to_path("zaken/123?status=open")
        self.assertEqual(result, "zaken/123")

        result = normalizer.normalize_to_path(
            "https://api.example.com/zaken?status=open&page=2"
        )
        self.assertEqual(result, "zaken")

    def test_normalize_to_path_base_path_only(self):
        """Test normalizing path that is exactly the base path."""
        normalizer = URLNormalizer("https://api.example.com/api/v1")

        result = normalizer.normalize_to_path("/api/v1")
        self.assertEqual(result, "")

        result = normalizer.normalize_to_path("api/v1")
        self.assertEqual(result, "")

    def test_extract_query_params_no_params(self):
        """Test extracting query params from URL without params."""
        normalizer = URLNormalizer("https://api.example.com")

        path, params = normalizer.extract_query_params("zaken/123")

        self.assertEqual(path, "zaken/123")
        self.assertEqual(params, {})

    def test_extract_query_params_single_values(self):
        """Test extracting query params with single values."""
        normalizer = URLNormalizer("https://api.example.com")

        path, params = normalizer.extract_query_params("zaken?status=open&page=2")

        self.assertEqual(path, "zaken")
        self.assertEqual(params, {"status": "open", "page": "2"})

    def test_extract_query_params_multiple_values(self):
        """Test extracting query params with multiple values."""
        normalizer = URLNormalizer("https://api.example.com")

        path, params = normalizer.extract_query_params("zaken?tag=urgent&tag=review")

        self.assertEqual(path, "zaken")
        # Multiple values should remain as list
        self.assertEqual(params, {"tag": ["urgent", "review"]})

    def test_extract_query_params_full_url(self):
        """Test extracting query params from full URL."""
        normalizer = URLNormalizer("https://api.example.com/api/v1")

        path, params = normalizer.extract_query_params(
            "https://api.example.com/api/v1/zaken?status=open&page=2"
        )

        self.assertEqual(path, "zaken")
        self.assertEqual(params, {"status": "open", "page": "2"})

    def test_strip_base_url_matching(self):
        """Test stripping base URL that matches."""
        normalizer = URLNormalizer("https://api.example.com/api/v1")

        result = normalizer.strip_base_url("https://api.example.com/api/v1/zaken/123")
        self.assertEqual(result, "zaken/123")

    def test_strip_base_url_different(self):
        """Test stripping base URL that doesn't match."""
        normalizer = URLNormalizer("https://api.example.com/api/v1")

        result = normalizer.strip_base_url("https://other.com/api/v2/zaken/123")
        self.assertEqual(result, "api/v2/zaken/123")

    def test_join_path_simple(self):
        """Test joining simple path parts."""
        normalizer = URLNormalizer("https://api.example.com")

        result = normalizer.join_path("zaken", "123", "status")
        self.assertEqual(result, "zaken/123/status")

    def test_join_path_with_slashes(self):
        """Test joining path parts with leading/trailing slashes."""
        normalizer = URLNormalizer("https://api.example.com")

        result = normalizer.join_path("/zaken/", "/123/", "/status/")
        self.assertEqual(result, "zaken/123/status")

    def test_join_path_empty_parts(self):
        """Test joining path with empty parts."""
        normalizer = URLNormalizer("https://api.example.com")

        result = normalizer.join_path("zaken", "", "123")
        self.assertEqual(result, "zaken/123")

    def test_join_path_single_part(self):
        """Test joining with single part."""
        normalizer = URLNormalizer("https://api.example.com")

        result = normalizer.join_path("zaken")
        self.assertEqual(result, "zaken")

    def test_join_path_no_parts(self):
        """Test joining with no parts."""
        normalizer = URLNormalizer("https://api.example.com")

        result = normalizer.join_path()
        self.assertEqual(result, "")

    def test_no_base_path(self):
        """Test normalizer with no base path."""
        normalizer = URLNormalizer("https://api.example.com")

        self.assertEqual(normalizer.base_path, "")

        result = normalizer.normalize_to_path("https://api.example.com/zaken/123")
        self.assertEqual(result, "zaken/123")

        result = normalizer.normalize_to_path("/zaken/123")
        self.assertEqual(result, "zaken/123")
