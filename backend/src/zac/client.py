from zds_client.log import Log
from zgw_consumers.client import ZGWClient
from zgw_consumers.nlx import NLXClientMixin


class DisabledLog(Log):
    """
    Do not log any requests in memory.

    * this prevents memory leaking
    * the default implementation is not thread-safe, yet we use this client in thread
      pools
    * we're not visualizing this anywhere anyway
    """


class Client(NLXClientMixin, ZGWClient):
    _log = DisabledLog()

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
