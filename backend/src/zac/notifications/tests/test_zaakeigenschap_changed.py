from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

import requests_mock
from elasticsearch_dsl import Index
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.models import User
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
from zac.tests.compat import mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
    OBJECT_RESPONSE,
    STATUS_RESPONSE,
    STATUSTYPE_RESPONSE,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKTYPE,
    ZAAKTYPE_RESPONSE,
    ZAKEN_ROOT,
)

EIGENSCHAP = f"{CATALOGI_ROOT}eigenschappen/69e98129-1f0d-497f-bbfb-84b88137edbc"
ZAAKEIGENSCHAP = f"{ZAAK}/zaakeigenschappen/69e98129-1f0d-497f-bbfb-84b88137edbc"
ZAAK_RESPONSE["eigenschappen"] = [ZAAKEIGENSCHAP]

# UPDATED: snake_case keys
NOTIFICATION_CREATE = {
    "kanaal": "zaken",
    "hoofd_object": ZAAK,
    "resource": "zaakeigenschap",
    "resource_url": ZAAKEIGENSCHAP,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "zaakvertrouwelijk",
    },
}
NOTIFICATION_DESTROY = {
    "kanaal": "zaken",
    "hoofd_object": ZAAK,
    "resource": "zaakeigenschap",
    "resource_url": ZAAKEIGENSCHAP,
    "actie": "destroy",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "zaakvertrouwelijk",
    },
}


@requests_mock.Mocker()
class ZaakEigenschapChangedTests(ClearCachesMixin, ESMixin, APITestCase):
    def test_zaakeigenschap_created_indexed_in_es(self, rm, *mocks):
        Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)
        eigenschap = {
            "url": EIGENSCHAP,
            "zaaktype": ZAAKTYPE,
            "specificatie": {
                "formaat": "tekst",
                "groep": "test",
                "lengte": "10",
                "kardinaliteit": "",
                "waardenverzameling": [],
            },
            "naam": "propname",
            "definitie": "some-definition",
        }
        zaakeigenschap = {
            "url": ZAAKEIGENSCHAP,
            "eigenschap": EIGENSCHAP,
            "zaak": ZAAK,
            "naam": "propname",
            "waarde": "propvalue",
        }
        rm.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={ZAAKTYPE}",
            json=paginated_response([eigenschap]),
        )
        rm.get(f"{ZAAK}/zaakeigenschappen", json=[zaakeigenschap])

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.zaaktype = create_zaak_document(
            zaak
        ).zaaktype  # safe-guard if needed
        zaak_document.save()
        self.refresh_index()

        self.assertEqual(zaak_document.eigenschappen, {})

        user = User.objects.create(
            username="notifs", first_name="Mona Yoko", last_name="Surname"
        )
        self.client.force_authenticate(user=user)
        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_CREATE)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)
        self.assertEqual(
            zaak_document.eigenschappen, {"tekst": {"propname": "propvalue"}}
        )

    def test_zaakeigenschap_destroyed_indexed_in_es(self, rm, *mocks):
        Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)
        rm.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={ZAAKTYPE}",
            json=paginated_response([]),
        )
        rm.get(f"{ZAAK}/zaakeigenschappen", json=[])

        user = User.objects.create(
            username="notifs", first_name="Mona Yoko", last_name="Surname"
        )
        self.client.force_authenticate(user=user)

        path = reverse("notifications:callback")

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.zaaktype = create_zaak_document(zaak).zaaktype
        zaak_document.eigenschappen = {"tekst": {"propname": "propvalue"}}
        zaak_document.save()
        self.refresh_index()

        # UPDATED: patch target to new module path
        with patch(
            "zac.notifications.handlers.zaken.invalidate_zaakeigenschappen_cache"
        ) as mock_invalidate_zei_cache:
            response = self.client.post(path, NOTIFICATION_DESTROY)

        mock_invalidate_zei_cache.assert_called_once()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)
        self.assertEqual(zaak_document.eigenschappen, {})
