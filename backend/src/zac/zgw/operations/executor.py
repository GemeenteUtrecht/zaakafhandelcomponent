"""
Operation execution utilities for ZGW API client.

This module provides utilities for executing HTTP requests with proper error handling.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ape_pie import APIClient

    from zac.zgw.utils.errors import ErrorHandler


class OperationExecutor:
    """
    Executor for HTTP requests with error handling.

    This class handles:
    - HTTP request dispatch (GET, POST, PUT, PATCH, DELETE)
    - Response error handling and conversion
    - Request kwargs merging
    """

    def __init__(self, client: "APIClient", error_handler: "ErrorHandler"):
        """
        Initialize the operation executor.

        Args:
            client: The APIClient instance to use for requests
            error_handler: ErrorHandler for response error handling
        """
        self.client = client
        self.error_handler = error_handler

    def execute(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
        **request_kwargs,
    ) -> Any:
        """
        Execute an HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: Relative path for the request
            data: Request body data (for POST/PUT/PATCH)
            params: Query parameters
            headers: Request headers
            **request_kwargs: Additional request kwargs

        Returns:
            Response data (parsed JSON)

        Raises:
            ClientError: If the response has an HTTP error status

        Examples:
            >>> executor = OperationExecutor(client, error_handler)
            >>> data = executor.execute("GET", "zaken", params={"status": "open"})
            >>> zaak = executor.execute("POST", "zaken", data={"zaaktype": "..."})
        """
        # Build request kwargs
        kwargs = self._build_request_kwargs(params, headers, **request_kwargs)

        # Add data for POST/PUT/PATCH requests
        if data is not None and method.upper() in ["POST", "PUT", "PATCH"]:
            kwargs["json"] = data

        # Dispatch the HTTP request
        response = self._dispatch_request(method.upper(), path, **kwargs)

        # Handle errors
        self.error_handler.handle_response(response)

        # Return parsed response
        if response.content:
            return response.json()
        return {}

    def _build_request_kwargs(
        self, params: dict | None, headers: dict | None, **additional_kwargs
    ) -> dict:
        """
        Build request kwargs by merging params, headers, and additional kwargs.

        Args:
            params: Query parameters
            headers: Request headers
            **additional_kwargs: Additional request kwargs

        Returns:
            Merged request kwargs dict
        """
        kwargs = {}

        # Add query parameters
        if params:
            kwargs["params"] = params

        # Add headers
        if headers:
            kwargs["headers"] = headers

        # Merge additional kwargs
        kwargs.update(additional_kwargs)

        return kwargs

    def _dispatch_request(self, method: str, path: str, **kwargs):
        """
        Dispatch HTTP request using the appropriate client method.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: Relative path
            **kwargs: Request kwargs

        Returns:
            requests.Response object

        Raises:
            ValueError: If HTTP method is not supported
        """
        method_dispatch = {
            "GET": self.client.get,
            "POST": self.client.post,
            "PUT": self.client.put,
            "PATCH": self.client.patch,
            "DELETE": self.client.delete,
        }

        if method not in method_dispatch:
            raise ValueError(f"Unsupported HTTP method: {method}")

        return method_dispatch[method](path, **kwargs)
