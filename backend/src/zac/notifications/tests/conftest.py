import pytest


@pytest.fixture
def zaak_url() -> str:
    return "https://openzaak.example.nl/zaken/123"


@pytest.fixture
def eio_url() -> str:
    return "https://drc.example.nl/enkelvoudiginformatieobjecten/abc"


@pytest.fixture
def dummy_notification():
    def _make(
        kanaal="zaken",
        resource="zaak",
        actie="update",
        hoofd_object="URL",
        resource_url=None,
        kenmerken=None,
    ):
        data = {
            "kanaal": kanaal,
            "resource": resource,
            "actie": actie,
            "hoofd_object": hoofd_object,
        }
        if resource_url:
            data["resource_url"] = resource_url
        if kenmerken:
            data["kenmerken"] = kenmerken
        return data

    return _make
