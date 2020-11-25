import time
from uuid import UUID, uuid4

from zds_client.log import Log
from zgw_consumers.client import ZGWClient
from zgw_consumers.nlx import NLXClientMixin


class DurationLog(Log):

    durations = {}

    @classmethod
    def add(cls, service: str, url: str, method: str, *args, **kwargs):
        # find the matchin request
        for request_id, info in cls.durations.items():
            request = info["request"]
            if request == (service, url, method, request_id):
                break
        else:
            raise ValueError("request not found in durations log")

        duration = cls.durations.pop(request_id)["duration"]

        super().add(service, url, method, *args, **kwargs)

        entry = next(
            (
                entry
                for entry in reversed(cls._entries)
                if entry["service"] == service
                and entry["request"]["url"] == url
                and entry["request"]["method"] == method
            )
        )
        entry["duration"] = duration

    def add_duration(self, request_id: UUID, duration: int):
        try:
            self.durations[request_id]["duration"] = duration
        except KeyError:
            pass


class Client(NLXClientMixin, ZGWClient):
    _log = DurationLog()
    request_starts = {}

    def pre_request(self, method, url, **kwargs) -> UUID:
        super().pre_request(method, url, **kwargs)

        request_id = uuid4()
        self.request_starts[request_id] = time.time()
        request = (self.service, url, method, request_id)
        self._log.durations[request_id] = {"request": request, "duration": 0}
        return request_id

    def post_response(self, request_id, response_json) -> None:
        super().post_response(request_id, response_json)

        start = self.request_starts.pop(request_id)
        duration = (time.time() - start) * 1000
        self._log.add_duration(request_id, int(duration))
