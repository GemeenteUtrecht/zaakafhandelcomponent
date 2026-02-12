import threading

from django.conf import settings

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session_lock = threading.Lock()
_shared_session: Session | None = None


def get_retry_strategy() -> Retry:
    return Retry(
        total=settings.REQUESTS_RETRY_TOTAL,
        backoff_factor=settings.REQUESTS_RETRY_BACKOFF_FACTOR,
        status_forcelist=settings.REQUESTS_RETRY_STATUS_FORCELIST,
        allowed_methods=["GET", "HEAD", "OPTIONS"],
        raise_on_status=False,
    )


def get_http_adapter() -> HTTPAdapter:
    return HTTPAdapter(
        max_retries=get_retry_strategy(),
        pool_connections=settings.REQUESTS_POOL_CONNECTIONS,
        pool_maxsize=settings.REQUESTS_POOL_MAXSIZE,
    )


def mount_retry_adapter(session: Session) -> None:
    """Mount a retry-enabled HTTPAdapter on a requests.Session (or subclass)."""
    adapter = get_http_adapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)


def get_session() -> Session:
    """
    Return a shared requests.Session with retry and connection pooling.

    The session is created once and reused across calls. This is safe for
    concurrent use from multiple threads as long as session-level state
    (cookies, auth) is not modified — all auth is passed via per-request
    headers in ZAC.
    """
    global _shared_session
    if _shared_session is None:
        with _session_lock:
            if _shared_session is None:
                session = Session()
                mount_retry_adapter(session)
                _shared_session = session
    return _shared_session
