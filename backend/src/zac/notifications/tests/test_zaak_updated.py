from copy import deepcopy
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from elasticsearch_dsl import Index
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.models import User
from zac.activities.tests.factories import ActivityFactory, ActivityStatuses
from zac.core.services import get_zaak
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import (
    create_object_document,
    create_related_zaak_document,
    create_zaak_document,
)
from zac.elasticsearch.documents import (
    InformatieObjectDocument,
    ObjectDocument,
    RolDocument,
    ZaakDocument,
)
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get
from zgw.models.zrc import Zaak

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
    OBJECT_RESPONSE,
    STATUS,
    STATUS_RESPONSE,
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
class ZaakUpdateTests(ClearCachesMixin, ESMixin, APITestCase):
    """
    Test that the appropriate actions happen on zaak-update notifications.
    """

    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_OBJECTEN).delete(ignore=404)
        Index(settings.ES_INDEX_DOCUMENTEN).delete(ignore=404)

        if init:
            ObjectDocument.init()
            InformatieObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_OBJECTEN).refresh()
        Index(settings.ES_INDEX_DOCUMENTEN).refresh()

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.zrc = Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        cls.ztc = Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_get_zaak_zaak_updated(self, rm):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
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
                super().setUp()  # clear cache
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
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
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

    def test_zaak_with_rollen_updated_indexed_in_es(self, rm):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)

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

    def test_zaak_updated_omschrijving_update_in_informatie_and_objecten_indices(
        self, rm
    ):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)

        path = reverse("notifications:callback")

        #  create zaak_document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.save()

        # create object document
        object_document = create_object_document(OBJECT_RESPONSE)
        related_zaak_document = create_related_zaak_document(zaak)
        object_document.related_zaken = [related_zaak_document]
        object_document.save()
        self.refresh_index()

        self.assertEqual(zaak_document.omschrijving, ZAAK_RESPONSE["omschrijving"])
        self.assertEqual(zaak_document.meta.version, 1)
        self.assertEqual(object_document.related_zaken, [related_zaak_document])
        self.assertEqual(object_document.meta.version, 1)

        # Update zaak api response
        new_response = {
            **ZAAK_RESPONSE,
            "omschrijving": "some updated omschrijving",
        }
        mock_resource_get(rm, new_response)

        response = self.client.post(path, NOTIFICATION)
        self.refresh_index()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)
        self.assertEqual(
            zaak_document.omschrijving,
            "some updated omschrijving",
        )
        self.assertEqual(zaak_document.meta.version, 2)

        object_document = ObjectDocument.get(id=object_document.meta.id)
        self.assertEqual(
            object_document.related_zaken[0].omschrijving,
            "some updated omschrijving",
        )
        self.assertEqual(object_document.meta.version, 2)

    def test_zaak_updated_is_closed(self, rm):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        zaak = deepcopy(ZAAK_RESPONSE)
        zaak["status"] = STATUS
        mock_resource_get(rm, zaak)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        statustype = deepcopy(STATUSTYPE_RESPONSE)
        statustype["is_eindstatus"] = True
        mock_resource_get(rm, statustype)

        path = reverse("notifications:callback")

        activity = ActivityFactory.create(
            zaak=zaak["url"], status=ActivityStatuses.on_going
        )
        with patch(
            "zac.notifications.handlers.bulk_lock_review_requests_for_zaak"
        ) as mock_bulk_lock_rr_for_zaak:
            with patch(
                "zac.notifications.handlers.bulk_close_all_documents_for_zaak"
            ) as mock_bulk_close_all_documents_for_zaak:
                with patch(
                    "zac.notifications.handlers.lock_checklist_for_zaak"
                ) as mock_lock_checklist_for_zaak:
                    response = self.client.post(path, NOTIFICATION)

        mock_bulk_lock_rr_for_zaak.assert_called_once()
        mock_bulk_close_all_documents_for_zaak.assert_called_once()
        mock_lock_checklist_for_zaak.assert_called_once()

        activity.refresh_from_db()
        self.assertEqual(activity.status, ActivityStatuses.finished)
        self.assertEqual(activity.user_assignee, None)
        self.assertEqual(activity.group_assignee, None)
