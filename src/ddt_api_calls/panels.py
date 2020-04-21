import time

from django.utils.translation import gettext_lazy as _, ngettext

import requests
import requests_mock
from debug_toolbar.panels import Panel
from requests_mock import adapter, exceptions
from requests_mock.mocker import _original_send

# TODO: persist data over requests - POST followed by redirect does not display the
# API calls made.


class PanelMocker(requests_mock.Mocker):
    def start(self):
        """Start mocking requests.

        Install the adapter and the wrappers required to intercept requests.
        """
        if self._last_send:
            raise RuntimeError("Mocker has already been started")

        self._last_send = requests.Session.send

        def _fake_get_adapter(session, url):
            return self._adapter

        def _fake_send(session, request, **kwargs):
            real_get_adapter = requests.Session.get_adapter
            requests.Session.get_adapter = _fake_get_adapter

            # NOTE(jamielennox): self._last_send vs _original_send. Whilst it
            # seems like here we would use _last_send there is the possibility
            # that the user has messed up and is somehow nesting their mockers.
            # If we call last_send at this point then we end up calling this
            # function again and the outer level adapter ends up winning.
            # All we really care about here is that our adapter is in place
            # before calling send so we always jump directly to the real
            # function so that our most recently patched send call ends up
            # putting in the most recent adapter. It feels funny, but it works.

            start = time.time()

            try:
                return _original_send(session, request, **kwargs)
            except exceptions.NoMockAddress:
                if not self._real_http:
                    raise
            except adapter._RunRealHTTP:
                # this mocker wants you to run the request through the real
                # requests library rather than the mocking. Let it.
                pass
            finally:
                requests.Session.get_adapter = real_get_adapter

            req = next(r for r in self.request_history if r._request == request)

            try:
                response = _original_send(session, request, **kwargs)
            except Exception:
                raise
            else:
                req.status_code = response.status_code
            finally:
                end = time.time()
                duration = (end - start) * 1000
                req.timing = (start, end, int(duration))
            return response

        requests.Session.send = _fake_send


class APICallsPanel(Panel):
    """
    Django Debug Toolbar panel to track python-requests calls.
    """

    title = _("API calls")
    template = "ddt_api_calls/requests.html"

    def enable_instrumentation(self):
        if not self.toolbar.request.is_ajax():
            self.mocker = PanelMocker(real_http=True)
            self.mocker.start()

    def disable_instrumentation(self):
        if not self.toolbar.request.is_ajax():
            self.mocker.stop()

    @property
    def nav_subtitle(self) -> str:
        num_calls = len(self.mocker.request_history)

        if num_calls:
            min_start = min(req.timing[0] for req in self.mocker.request_history)
            max_end = max(req.timing[1] for req in self.mocker.request_history)
            total_time = int((max_end - min_start) * 1000)
        else:
            total_time = 0

        return ngettext(
            "1 API call made in {duration}ms",
            "{n} API calls made in {duration}ms",
            num_calls,
        ).format(n=num_calls, duration=total_time)

    def generate_stats(self, request, response):
        requests = self.mocker.request_history
        stats = {
            "requests": requests,
        }
        self.record_stats(stats)
