"""
URL normalization utilities for ZGW API client.

This module provides utilities for normalizing URLs and paths for API requests,
handling both full URLs and relative paths.
"""

from urllib.parse import parse_qs, urlparse


class URLNormalizer:
    """
    Normalizer for URLs and paths used in API requests.

    This class handles:
    - Converting full URLs to relative paths
    - Stripping base URLs and base paths
    - Extracting query parameters from URLs
    - Normalizing relative paths
    """

    def __init__(self, base_url: str):
        """
        Initialize the URL normalizer.

        Args:
            base_url: The base URL of the API (e.g., "https://api.example.com/api/v1")
        """
        self.base_url = base_url.rstrip("/")

        # Extract base path from base_url for stripping from paths
        parsed = urlparse(self.base_url)
        self.base_path = parsed.path.strip("/")

    def normalize_to_path(self, url: str) -> str:
        """
        Convert a full URL or relative path to a normalized relative path.

        This strips the base URL and base path to get just the resource path.
        Query parameters are stripped (use extract_query_params to get them).

        Args:
            url: Full URL or relative path

        Returns:
            Normalized relative path without leading slash

        Examples:
            >>> normalizer = URLNormalizer("https://api.example.com/api/v1")
            >>> normalizer.normalize_to_path("https://api.example.com/api/v1/zaken/123")
            'zaken/123'
            >>> normalizer.normalize_to_path("/api/v1/zaken/123")
            'zaken/123'
            >>> normalizer.normalize_to_path("zaken/123")
            'zaken/123'
            >>> normalizer.normalize_to_path("zaken/123?status=open")
            'zaken/123'
        """
        # Strip query parameters first
        if "?" in url:
            url = url.split("?", 1)[0]

        if self.is_full_url(url):
            # Full URL - strip base_url
            if url.startswith(self.base_url):
                path = url[len(self.base_url) :].lstrip("/")
            else:
                # URL doesn't match base_url - extract just the path
                parsed = urlparse(url)
                path = parsed.path.lstrip("/")
        else:
            # Relative path - strip leading slash
            path = url.lstrip("/")

            # Strip base path if present
            if self.base_path:
                if path.startswith(self.base_path + "/"):
                    path = path[len(self.base_path) + 1 :]
                elif path == self.base_path:
                    path = ""

        return path

    def extract_query_params(self, url: str) -> tuple[str, dict]:
        """
        Extract path and query parameters from a URL.

        Args:
            url: URL or path with optional query parameters

        Returns:
            Tuple of (normalized_path, query_params_dict)
            Query params dict has single values flattened (list of 1 -> value)

        Examples:
            >>> normalizer = URLNormalizer("https://api.example.com")
            >>> path, params = normalizer.extract_query_params("zaken?status=open&page=2")
            >>> path
            'zaken'
            >>> params
            {'status': 'open', 'page': '2'}
        """
        if "?" not in url:
            return self.normalize_to_path(url), {}

        # Split URL into path and query parts
        path_part, query_part = url.split("?", 1)

        # Normalize the path part
        normalized_path = self.normalize_to_path(path_part)

        # Parse query parameters
        query_params = parse_qs(query_part)

        # Flatten single-value params
        flattened_params = {}
        for key, values in query_params.items():
            flattened_params[key] = values[0] if len(values) == 1 else values

        return normalized_path, flattened_params

    def is_full_url(self, url: str) -> bool:
        """
        Check if a URL is a full URL (starts with http:// or https://).

        Args:
            url: URL or path to check

        Returns:
            True if full URL, False if relative path

        Examples:
            >>> normalizer = URLNormalizer("https://api.example.com")
            >>> normalizer.is_full_url("https://api.example.com/zaken")
            True
            >>> normalizer.is_full_url("zaken/123")
            False
            >>> normalizer.is_full_url("/api/v1/zaken")
            False
        """
        return url.startswith("http://") or url.startswith("https://")

    def strip_base_url(self, url: str) -> str:
        """
        Strip the base URL from a full URL, leaving the path.

        If the URL doesn't start with the base URL, extracts just the path component.

        Args:
            url: Full URL

        Returns:
            Path without base URL

        Examples:
            >>> normalizer = URLNormalizer("https://api.example.com/api/v1")
            >>> normalizer.strip_base_url("https://api.example.com/api/v1/zaken/123")
            'zaken/123'
            >>> normalizer.strip_base_url("https://other.com/zaken/123")
            'zaken/123'
        """
        if url.startswith(self.base_url):
            return url[len(self.base_url) :].lstrip("/")

        # URL doesn't match base_url - extract just the path
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")

        # Strip base path if present
        if self.base_path:
            if path.startswith(self.base_path + "/"):
                path = path[len(self.base_path) + 1 :]
            elif path == self.base_path:
                path = ""

        return path

    def join_path(self, *parts: str) -> str:
        """
        Join path parts into a normalized path.

        Args:
            *parts: Path parts to join

        Returns:
            Joined path without leading slash

        Examples:
            >>> normalizer = URLNormalizer("https://api.example.com")
            >>> normalizer.join_path("zaken", "123", "status")
            'zaken/123/status'
            >>> normalizer.join_path("/zaken/", "/123/")
            'zaken/123'
        """
        # Strip leading/trailing slashes from each part
        cleaned_parts = [part.strip("/") for part in parts if part.strip("/")]
        return "/".join(cleaned_parts)
