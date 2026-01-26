"""
Unit tests for ErrorHandler.
"""

from unittest.mock import Mock

from django.test import TestCase

from requests.exceptions import HTTPError
from zds_client.client import ClientError

from zac.zgw.utils.errors import ErrorHandler


class ErrorHandlerTests(TestCase):
    """Tests for the ErrorHandler class."""

    def test_handle_response_success(self):
        """Test that successful responses pass through without error."""
        response = Mock()
        response.status_code = 200
        response.raise_for_status = Mock()  # Does nothing for 2xx

        # Should not raise any exception
        ErrorHandler.handle_response(response)
        response.raise_for_status.assert_called_once()

    def test_handle_response_404_error(self):
        """Test that 404 errors are converted to ClientError."""
        response = Mock()
        response.status_code = 404
        response.content = b'{"detail": "Not found"}'
        response.json = Mock(return_value={"detail": "Not found"})

        def raise_http_error():
            raise HTTPError(response=response)

        response.raise_for_status = raise_http_error

        with self.assertRaises(ClientError) as context:
            ErrorHandler.handle_response(response)

        # Verify ClientError was raised with correct data
        self.assertEqual(context.exception.args[0], {"detail": "Not found"})

    def test_handle_response_500_error(self):
        """Test that 500 errors are converted to ClientError."""
        response = Mock()
        response.status_code = 500
        response.content = b'{"error": "Internal server error"}'
        response.json = Mock(return_value={"error": "Internal server error"})

        def raise_http_error():
            raise HTTPError(response=response)

        response.raise_for_status = raise_http_error

        with self.assertRaises(ClientError) as context:
            ErrorHandler.handle_response(response)

        self.assertEqual(context.exception.args[0], {"error": "Internal server error"})

    def test_handle_response_empty_content(self):
        """Test that errors with empty content raise ClientError with None."""
        response = Mock()
        response.status_code = 404
        response.content = b""

        def raise_http_error():
            raise HTTPError(response=response)

        response.raise_for_status = raise_http_error

        with self.assertRaises(ClientError) as context:
            ErrorHandler.handle_response(response)

        # Should have None as error data when content is empty
        self.assertIsNone(context.exception.args[0])

    def test_handle_response_invalid_json(self):
        """Test that errors with invalid JSON raise ClientError with None."""
        response = Mock()
        response.status_code = 500
        response.content = b"Not JSON"
        response.json = Mock(side_effect=Exception("Invalid JSON"))

        def raise_http_error():
            raise HTTPError(response=response)

        response.raise_for_status = raise_http_error

        with self.assertRaises(ClientError) as context:
            ErrorHandler.handle_response(response)

        # Should have None as error data when JSON parsing fails
        self.assertIsNone(context.exception.args[0])

    def test_wrap_response_decorator_success(self):
        """Test that wrap_response decorator passes successful responses."""

        @ErrorHandler.wrap_response
        def successful_request():
            response = Mock()
            response.status_code = 200
            response.raise_for_status = Mock()
            return response

        # Should not raise any exception
        result = successful_request()
        self.assertEqual(result.status_code, 200)

    def test_wrap_response_decorator_error(self):
        """Test that wrap_response decorator converts errors to ClientError."""

        @ErrorHandler.wrap_response
        def failing_request():
            response = Mock()
            response.status_code = 404
            response.content = b'{"detail": "Not found"}'
            response.json = Mock(return_value={"detail": "Not found"})

            def raise_http_error():
                raise HTTPError(response=response)

            response.raise_for_status = raise_http_error
            return response

        with self.assertRaises(ClientError):
            failing_request()

    def test_error_chaining(self):
        """Test that HTTPError is chained as the cause of ClientError."""
        response = Mock()
        response.status_code = 404
        response.content = b'{"detail": "Not found"}'
        response.json = Mock(return_value={"detail": "Not found"})

        def raise_http_error():
            raise HTTPError(response=response)

        response.raise_for_status = raise_http_error

        with self.assertRaises(ClientError) as context:
            ErrorHandler.handle_response(response)

        # Verify exception chaining
        self.assertIsInstance(context.exception.__cause__, HTTPError)
