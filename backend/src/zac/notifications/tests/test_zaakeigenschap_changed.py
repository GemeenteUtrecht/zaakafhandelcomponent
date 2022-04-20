from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.models import User
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import create_zaak_document, create_zaaktype_document
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response
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

EIGENSCHAP = f"{CATALOGI_ROOT}eigenschappen/69e98129-1f0d-497f-bbfb-84b88137edbc"
ZAAKEIGENSCHAP = f"{ZAAK}/zaakeigenschappen/69e98129-1f0d-497f-bbfb-84b88137edbc"
ZAAK_RESPONSE["eigenschappen"] = [ZAAKEIGENSCHAP]
NOTIFICATION_CREATE = {
    "kanaal": "zaken",
    "hoofdObject": ZAAK,
    "resource": "zaakeigenschap",
    "resourceUrl": ZAAKEIGENSCHAP,
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
    "hoofdObject": ZAAK,
    "resource": "zaakeigenschap",
    "resourceUrl": ZAAKEIGENSCHAP,
    "actie": "destroy",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "zaakvertrouwelijk",
    },
}


@requests_mock.Mocker()
class ZaakEigenschapChangedTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    @patch("zac.elasticsearch.api.get_zaakobjecten", return_value=[])
    def test_zaakeigenschap_created_indexed_in_es(self, rm, *mocks):
        Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=EIGENSCHAP,
            zaaktype=ZAAKTYPE,
            specificatie={
                "formaat": "tekst",
                "groep": "test",
                "lengte": "10",
                "kardinaliteit": "",
                "waardenverzameling": [],
            },
        )
        zaakeigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=ZAAKEIGENSCHAP,
            eigenschap=EIGENSCHAP,
            zaak=ZAAK,
            naam="propname",
            waarde="propvalue",
        )
        rm.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={ZAAKTYPE}",
            json=paginated_response([eigenschap]),
        )
        rm.get(f"{ZAAK}/zaakeigenschappen", json=[zaakeigenschap])

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.zaaktype = create_zaaktype_document(zaak.zaaktype)
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

    @patch("zac.elasticsearch.api.get_zaakobjecten", return_value=[])
    def test_zaakeigenschap_destroyed_indexed_in_es(self, rm, *mocks):
        Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
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
        zaak_document.zaaktype = create_zaaktype_document(zaak.zaaktype)
        zaak_document.eigenschappen = {"tekst": {"propname": "propvalue"}}
        zaak_document.save()
        self.refresh_index()

        response = self.client.post(path, NOTIFICATION_DESTROY)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)

        self.assertEqual(zaak_document.eigenschappen, {})
