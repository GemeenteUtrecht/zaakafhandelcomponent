from zac.notifications.handlers.documenten import InformatieObjectenHandler


def test_eio_update_indexes_and_caches(dummy_notification, monkeypatch, eio_url):
    h = InformatieObjectenHandler()

    monkeypatch.setattr(
        "zac.core.cache.invalidate_document_url_cache", lambda url: None
    )
    monkeypatch.setattr(
        "zac.core.cache.invalidate_document_other_cache", lambda doc: None
    )
    monkeypatch.setattr(
        "zac.core.services.get_document", lambda url: type("Doc", (), {"url": url})()
    )
    called = {"upd": 0}

    def _upd(doc):
        called["upd"] += 1

    monkeypatch.setattr("zac.elasticsearch.api.update_informatieobject_document", _upd)

    msg = dummy_notification(
        kanaal="documenten",
        resource="enkelvoudiginformatieobject",
        actie="update",
        hoofd_object=eio_url,
    )
    h.handle(msg)

    assert called["upd"] == 1
