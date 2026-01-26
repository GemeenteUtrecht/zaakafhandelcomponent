"""
Error handling utilities for ZGW API client.

This module provides utilities for handling HTTP errors and converting them
to backward-compatible ClientError exceptions.
"""

from requests.exceptions import HTTPError
from zds_client.client import ClientError


class ErrorHandler:
    """
    Handler for converting HTTP errors to ClientError for backward compatibility.

    In zgw-consumers <1.0, the ZGWClient raised ClientError for HTTP errors.
    In zgw-consumers 1.x with ape_pie, HTTPError is raised instead.
    This handler wraps responses to maintain backward compatibility.
    """

    @staticmethod
    def handle_response(response):
        """
        Check response status and raise ClientError if there's an HTTP error.

        This converts HTTPError to ClientError for backward compatibility with
        zgw-consumers <1.0 code that expects ClientError.

        Args:
            response: The requests.Response object

        Raises:
            ClientError: If the response has an HTTP error status

        Examples:
            >>> handler = ErrorHandler()
            >>> handler.handle_response(response)  # raises ClientError on 4xx/5xx
        """
        try:
            response.raise_for_status()
        except HTTPError as e:
            # Extract error details from response if available
            error_data = None
            if response.content:
                try:
                    error_data = response.json()
                except Exception:
                    # If we can't parse JSON, use None
                    pass

            raise ClientError(error_data) from e

    @staticmethod
    def wrap_response(func):
        """
        Decorator to automatically handle errors in response-returning functions.

        Args:
            func: Function that returns a requests.Response

        Returns:
            Decorated function that handles errors

        Examples:
            >>> @ErrorHandler.wrap_response
            >>> def make_request():
            >>>     return requests.get("https://api.example.com")
        """

        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            ErrorHandler.handle_response(response)
            return response

        return wrapper
