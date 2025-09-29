import types

from zac.notifications.handlers import utils
from zac.notifications.handlers.zaken import ZakenHandler


def test_zaak_update_invalidates_and_updates(dummy_notification, monkeypatch, zaak_url):
    h = ZakenHandler()

    # stub zaak
    dummy_zaak = types.SimpleNamespace(url=zaak_url, status=None)
    monkeypatch.setattr(utils, "retrieve_zaak", lambda url: dummy_zaak)

    # stubs for cache and ES updates
    calls = {"inv": 0, "doc": 0, "obj": 0, "docu": 0}
    monkeypatch.setattr(
        "zac.core.cache.invalidate_zaak_cache",
        lambda zaak: calls.__setitem__("inv", calls["inv"] + 1),
    )
    monkeypatch.setattr(
        "zac.elasticsearch.api.update_zaak_document",
        lambda zaak: calls.__setitem__("doc", calls["doc"] + 1),
    )
    monkeypatch.setattr(
        utils,
        "soft_update_related_zaak_in_objects",
        lambda zaak: calls.__setitem__("obj", calls["obj"] + 1),
    )
    monkeypatch.setattr(
        utils,
        "soft_update_related_zaak_in_docs",
        lambda zaak: calls.__setitem__("docu", calls["docu"] + 1),
    )

    msg = dummy_notification(resource="zaak", actie="update", hoofd_object=zaak_url)
    h.handle(msg)

    assert calls == {"inv": 1, "doc": 1, "obj": 1, "docu": 1}
