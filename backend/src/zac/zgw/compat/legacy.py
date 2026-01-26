"""
Backward compatibility utilities for zgw-consumers <1.0 API.

This module provides a mixin class that adds backward compatibility methods
and properties for code that was written against the old zgw-consumers API.
"""

import logging
from typing import Union

from requests import PreparedRequest

logger = logging.getLogger(__name__)


class BackwardCompatibilityMixin:
    """
    Mixin providing backward compatibility with zgw-consumers <1.0 API.

    This mixin adds methods and properties that existed in the old ZGWClient
    but are no longer part of the core API in zgw-consumers 1.x.

    Methods and properties provided:
    - auth_header: Property to get authorization headers
    - set_auth_value(): Set authentication dynamically
    - log: Property for timeline logging (disabled, returns empty list)
    - pre_request(): Hook for subclasses to modify requests
    - refresh_auth(): Refresh JWT tokens
    - operation_suffix_mapping: Mapping of method names to operation ID suffixes
    """

    def __init__(self, *args, **kwargs):
        """Initialize backward compatibility features."""
        super().__init__(*args, **kwargs)

        # Operation suffix mapping for backward compatibility with zds-client
        # Maps HTTP method names to operation ID suffixes used in OAS schemas
        self.operation_suffix_mapping = {
            "list": "_list",
            "retrieve": "_read",
            "create": "_create",
            "update": "_update",
            "partial_update": "_partial_update",
            "delete": "_delete",
        }

        # Add credentials() method to auth object for backward compatibility
        # In zgw-consumers <1.0, auth had a credentials() method
        # In zgw-consumers 1.x, auth objects are AuthBase subclasses without this method
        if (
            hasattr(self, "auth")
            and self.auth
            and not hasattr(self.auth, "credentials")
        ):
            self._wrap_auth_with_credentials()

    def _wrap_auth_with_credentials(self):
        """
        Add a credentials() method to the auth object for backward compatibility.

        Legacy code calls client.auth.credentials() to get auth headers.
        In zgw-consumers 1.x, auth objects don't have this method, so we add it.
        """

        def credentials():
            """Extract auth headers from the auth object."""
            req = PreparedRequest()
            req.headers = {}
            self.auth(req)
            return dict(req.headers)

        # Monkey-patch the credentials method onto the auth object
        self.auth.credentials = credentials

    def set_auth_value(self, auth_value: Union[str, dict]):
        """
        Set authentication headers dynamically.

        This method provides backward compatibility with the old ZGWClient API
        where auth could be set after instantiation.

        Args:
            auth_value: Either a dict of headers or an Authorization header value

        Examples:
            >>> client.set_auth_value("Bearer token123")
            >>> client.set_auth_value({"Authorization": "Bearer token123"})
        """
        # Store the auth value for the auth_header property
        if isinstance(auth_value, dict):
            self.auth_value = auth_value
        else:
            self.auth_value = {"Authorization": auth_value}

        # Apply these headers via _request_kwargs so they're included in all requests
        # but don't persist in the session across test boundaries
        if not hasattr(self, "_request_kwargs"):
            self._request_kwargs = {}
        if "headers" not in self._request_kwargs:
            self._request_kwargs["headers"] = {}
        self._request_kwargs["headers"].update(self.auth_value)

    @property
    def auth_header(self) -> dict[str, str]:
        """
        Return the authorization headers as a dictionary.

        This property provides backward compatibility with zgw-consumers <1.0.

        Returns:
            Dictionary of authorization headers

        Examples:
            >>> headers = client.auth_header
            >>> headers
            {'Authorization': 'Bearer token123'}
        """
        # Check if we have auth_value set via set_auth_value
        if hasattr(self, "auth_value") and self.auth_value:
            return self.auth_value

        # Otherwise, generate from the auth attribute (from Service configuration)
        if hasattr(self, "auth") and self.auth:
            req = PreparedRequest()
            req.headers = {}
            self.auth(req)
            return dict(req.headers)

        return {}

    @property
    def log(self):
        """
        Get timeline log entries for this service.

        Note: Logging is disabled in ZAC to prevent memory leaks in thread pools.
        Returns empty list for backward compatibility.

        Returns:
            Empty list (logging disabled)
        """
        return []

    def pre_request(self, method: str, url: str, **kwargs) -> dict:
        """
        Hook for subclasses to modify requests before they are sent.

        This is a backwards-compatibility hook for old zds-client API.
        Subclasses can override this to add headers or modify kwargs.

        Args:
            method: The HTTP method
            url: The request URL
            **kwargs: Request kwargs

        Returns:
            The (possibly modified) kwargs dict

        Examples:
            >>> class CustomClient(ZGWClient, BackwardCompatibilityMixin):
            ...     def pre_request(self, method, url, **kwargs):
            ...         kwargs = super().pre_request(method, url, **kwargs)
            ...         if 'headers' not in kwargs:
            ...             kwargs['headers'] = {}
            ...         kwargs['headers']['X-Custom'] = 'value'
            ...         return kwargs
        """
        return kwargs

    def refresh_auth(self):
        """
        Re-generate a JWT with the given credentials.

        If a client instance is long-lived, the JWT may expire leading to 403 errors.
        This method regenerates a new JWT with the same credentials.

        This is particularly useful in long-running processes like elasticsearch indexing
        that may run for hours.

        Examples:
            >>> client = service.build_client()
            >>> # ... long running operation ...
            >>> client.refresh_auth()  # Refresh expired JWT
        """
        if not hasattr(self, "auth") or not self.auth:
            return

        # For JWT auth, clear the cached credentials to force regeneration
        if hasattr(self.auth, "_credentials"):
            delattr(self.auth, "_credentials")
