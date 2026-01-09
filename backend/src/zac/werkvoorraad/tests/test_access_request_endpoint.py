from django.urls import reverse

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import (
    AccessRequestFactory,
    BlueprintPermissionFactory,
    UserFactory,
)
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.permissions import zaken_handle_access, zaken_inzien
from zac.core.rollen import Rol
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import create_rol_document
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


@requests_mock.Mocker()
class AccessRequestsTests(ClearCachesMixin, ESMixin, APITestCase):
    """
    Test the access requests API endpoint.

    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.endpoint = reverse(
            "werkvoorraad:access-requests",
        )

    def test_access_requests_no_permission(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_access_requests_permission(self, m):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="DOME",
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus["url"],
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            zaaktype=zaaktype["url"],
            startdatum="2021-02-12",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
        )

        rol_1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "initiator",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": f"{AssigneeTypeChoices.user}:{user}",
            },
        }
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, catalogus)
        zaak_document = self.create_zaak_document(zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(zaaktype)
        zaak_document.rollen = [create_rol_document(factory(Rol, rol_1))]
        zaak_document.save()
        self.refresh_index()

        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={zaaktype['catalogus']}",
            json=paginated_response([zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=user,
            policy={
                "catalogus": catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        self.access_request1 = AccessRequestFactory.create(zaak=zaak["url"])
        self.access_request2 = AccessRequestFactory.create()

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "accessRequests": [
                        {
                            "id": self.access_request1.id,
                            "requester": self.access_request1.requester.username,
                        }
                    ],
                    "zaak": {
                        "identificatie": zaak["identificatie"],
                        "bronorganisatie": zaak["bronorganisatie"],
                        "url": zaak["url"],
                        "status": {
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                            "statustype": None,
                            "url": None,
                        },
                        "zaaktype": {
                            "url": zaaktype["url"],
                            "catalogus": zaaktype["catalogus"],
                            "catalogusDomein": catalogus["domein"],
                            "omschrijving": zaaktype["omschrijving"],
                            "identificatie": zaaktype["identificatie"],
                        },
                        "omschrijving": zaak["omschrijving"],
                        "deadline": "2021-02-17T00:00:00Z",
                    },
                }
            ],
        )
