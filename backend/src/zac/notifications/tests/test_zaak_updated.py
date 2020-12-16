from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.models import APITypes, Service

from zac.accounts.models import User
from zac.core.services import get_zaak
from zac.elasticsearch.api import create_zaak_document
from zac.elasticsearch.documents import RolDocument, ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin

from .utils import BRONORGANISATIE, ZAAK, ZAAK_RESPONSE, ZAAKTYPE, mock_service_oas_get

NOTIFICATION = {
    "kanaal": "zaken",
    "hoofdObject": "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
    "resource": "zaak",
    "resourceUrl": "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
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
    Test that the appropriate actions happen on zaak-creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.zrc = Service.objects.create(
            api_root="https://some.zrc.nl/api/v1/", api_type=APITypes.zrc
        )

    def setUp(self):
        super().setUp()

        cache.clear()
        self.client.force_authenticate(user=self.user)

    @patch("zac.core.services.fetch_zaaktype", return_value=None)
    def test_get_zaak_resultaat_created(self, rm, mock_zaaktype):
        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zaken")
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        path = reverse("notifications:callback")

        matrix = [
            {"zaak_uuid": "f3ff2713-2f53-42ff-a154-16842309ad60"},
            {"zaak_url": ZAAK},
            {"zaak_uuid": "f3ff2713-2f53-42ff-a154-16842309ad60", "zaak_url": ZAAK},
        ]

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

    def test_zaak_updated_indexed_in_es(self, rm):
        path = reverse("notifications:callback")
        #  create zaak_document in ES
        old_response = ZAAK_RESPONSE.copy()
        zaak = factory(Zaak, old_response)
        zaak_document = create_zaak_document(zaak)

        self.assertEqual(
            zaak_document.vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduidingen.geheim,
        )
        self.assertEqual(zaak_document.meta.version, 1)

        # set up mock
        new_response = old_response.copy()
        new_response[
            "vertrouwelijkheidaanduiding"
        ] = VertrouwelijkheidsAanduidingen.confidentieel
        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zaken")
        rm.get(ZAAK, json=new_response)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)

        self.assertEqual(
            zaak_document.vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduidingen.confidentieel,
        )
        self.assertEqual(zaak_document.meta.version, 2)

    def test_zaak_with_rollen_updated_indexed_in_es(self, rm):
        path = reverse("notifications:callback")
        #  create zaak_document
        old_response = ZAAK_RESPONSE.copy()
        zaak = factory(Zaak, old_response)
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
        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zaken")
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
