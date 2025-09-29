from zac.notifications.handlers.objecten import ObjectenHandler


def test_object_destroy_updates_indexes(dummy_notification, monkeypatch):
    h = ObjectenHandler()

    deleted = {"obj": 0, "zobj": 0}
    monkeypatch.setattr(
        "zac.elasticsearch.api.delete_object_document",
        lambda url: deleted.__setitem__("obj", 1),
    )
    monkeypatch.setattr(
        "zac.contrib.objects.services.delete_zaakobjecten_of_object",
        lambda url: deleted.__setitem__("zobj", 1),
    )
    monkeypatch.setattr(
        "zac.core.cache.invalidate_fetch_object_cache", lambda url: None
    )

    msg = dummy_notification(
        kanaal="objecten", resource="object", actie="destroy", hoofd_object="obj-url"
    )
    h.handle(msg)

    assert deleted == {"obj": 1, "zobj": 1}
