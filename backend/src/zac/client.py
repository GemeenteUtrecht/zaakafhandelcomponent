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
