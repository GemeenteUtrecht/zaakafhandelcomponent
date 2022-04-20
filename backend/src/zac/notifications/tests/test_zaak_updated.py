from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.models import User
from zac.core.services import get_zaak
from zac.elasticsearch.api import create_zaak_document
from zac.elasticsearch.documents import RolDocument, ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get
from zgw.models.zrc import Zaak

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    STATUS,
    STATUS_RESPONSE,
    STATUSTYPE,
    STATUSTYPE_RESPONSE,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKTYPE,
    ZAAKTYPE_RESPONSE,
    ZAKEN_ROOT,
)

NOTIFICATION = {
    "kanaal": "zaken",
    "hoofdObject": ZAAK,
    "resource": "zaak",
    "resourceUrl": ZAAK,
    "actie": "update",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "geheim",
    },
}


@requests_mock.Mocker()
class ZaakUpdateTests(ESMixin, APITestCase):
    """
    Test that the appropriate actions happen on zaak-update notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.zrc = Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        cls.ztc = Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)

    def setUp(self):
        super().setUp()

        cache.clear()
        self.client.force_authenticate(user=self.user)

    def test_get_zaak_zaak_updated(self, rm, *mocks):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)

        path = reverse("notifications:callback")

        matrix = [
            {"zaak_uuid": "f3ff2713-2f53-42ff-a154-16842309ad60"},
            {"zaak_url": ZAAK},
            {"zaak_uuid": "f3ff2713-2f53-42ff-a154-16842309ad60", "zaak_url": ZAAK},
        ]

        #  create zaak_document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.save()
        self.refresh_index()

        for kwargs in matrix:
            with self.subTest(**kwargs):
                # call to populate cache
                get_zaak(**kwargs)
                self.assertEqual(rm.last_request.url, ZAAK)
                first_retrieve = rm.last_request

                response = self.client.post(path, NOTIFICATION)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

                num_calls_before = len(rm.request_history)

                # second call should not hit the cache
                get_zaak(**kwargs)

                self.assertEqual(rm.last_request.url, ZAAK)
                self.assertNotEqual(rm.last_request, first_retrieve)
                self.assertEqual(len(rm.request_history), num_calls_before + 1)

    @patch("zac.elasticsearch.api.get_zaakobjecten", return_value=[])
    def test_zaak_updated_indexed_in_es(self, rm, *mocks):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)

        path = reverse("notifications:callback")

        #  create zaak_document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.save()
        self.refresh_index()

        self.assertEqual(
            zaak_document.vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduidingen.geheim,
        )
        self.assertEqual(zaak_document.meta.version, 1)

        # set up mock
        new_response = {
            **ZAAK_RESPONSE,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.confidentieel,
        }
        mock_resource_get(rm, new_response)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)

        self.assertEqual(
            zaak_document.vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduidingen.confidentieel,
        )
        self.assertEqual(zaak_document.meta.version, 2)

    @patch("zac.elasticsearch.api.get_zaakobjecten", return_value=[])
    def test_zaak_with_rollen_updated_indexed_in_es(self, rm, *mocks):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        rm.get(STATUS, json=STATUS_RESPONSE)
        rm.get(STATUSTYPE, json=STATUSTYPE_RESPONSE)
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)

        path = reverse("notifications:callback")

        #  create zaak_document
        old_response = ZAAK_RESPONSE.copy()
        zaak = factory(Zaak, old_response)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)

        #  set rollen
        zaak_document.rollen = [
            RolDocument(
                url="https://some.zrc.nl/api/v1/rollen/12345",
                betrokkene_type="medewerker",
            ),
            RolDocument(
                url="https://some.zrc.nl/api/v1/rollen/6789",
                betrokkene_type="medewerker",
            ),
        ]
        zaak_document.save()
        self.refresh_index()

        self.assertEqual(
            zaak_document.vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduidingen.geheim,
        )
        self.assertEqual(len(zaak_document.rollen), 2)

        # set up mock
        new_response = old_response.copy()
        new_response[
            "vertrouwelijkheidaanduiding"
        ] = VertrouwelijkheidsAanduidingen.confidentieel
        mock_service_oas_get(rm, "https://some.zrc.nl/", "zrc")
        rm.get(ZAAK, json=new_response)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)

        self.assertEqual(
            zaak_document.vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduidingen.confidentieel,
        )
        # check that rollen were kept during update
        self.assertEqual(len(zaak_document.rollen), 2)
