from zac.notifications.handlers.zaken import ZakenHandler
from zac.notifications.routing import RoutingHandler


def test_routing_calls_correct_handler(dummy_notification, monkeypatch):
    called = {"count": 0}

    class Dummy(ZakenHandler):
        def handle(self, msg):
            called["count"] += 1

    handler = RoutingHandler({"zaken": Dummy()})
    handler.handle(dummy_notification(kanaal="zaken"))

    assert called["count"] == 1
