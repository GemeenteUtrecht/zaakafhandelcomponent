from zac.zgw_client import ZGWClient

try:
    from zgw_consumers.nlx import NLXClientMixin
except ImportError:
    # zgw-consumers 1.x may have moved or removed NLXClientMixin
    # For now, use a no-op mixin for compatibility
    class NLXClientMixin:
        """Placeholder for NLX support if zgw-consumers 1.x removed it."""


class Client(NLXClientMixin, ZGWClient):
    """
    ZAC's custom ZGW API client with NLX support.

    Extends the base ZGWClient with NLX URL rewriting capabilities
    and JWT refresh functionality for long-lived client instances.
    """

    def refresh_auth(self):
        """
        Re-generate a JWT with the given credentials.

        If a client instance is long-lived, the JWT may expire leading to 403 errors.
        This extra method adds the option to generate a new JWT with the same credentials.
        """
        if not self.auth:
            return

        if hasattr(self.auth, "_credentials"):
            delattr(self.auth, "_credentials")
