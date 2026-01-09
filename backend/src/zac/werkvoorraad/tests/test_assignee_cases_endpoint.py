from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.zaken import Rol
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import SuperUserFactory
from zac.camunda.constants import AssigneeTypeChoices
from zac.elasticsearch.api import create_rol_document
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zgw.models.zrc import Zaak

ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


@requests_mock.Mocker()
class AssigneeCasesTests(ESMixin, APITransactionTestCase):
    """
    Test the assignee cases API endpoint.
    """

    endpoint = reverse_lazy(
        "werkvoorraad:cases",
    )

    def test_cases_endpoint(self, m, *mocks):
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}/catalogussen/c25a4e4b-c19c-4ab9-a51b-1e9a65890383",
        )

        zaak_1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            startdatum="2021-02-12",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
            zaaktype=zaaktype["url"],
        )
        zaak_model_1 = factory(Zaak, zaak_1)
        zaak_model_1.zaaktype = factory(ZaakType, zaaktype)

        zaak_2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e39-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0011",
            bronorganisatie="123456782",
            startdatum="2021-02-13",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
            zaaktype=zaaktype["url"],
        )
        zaak_model_2 = factory(Zaak, zaak_2)
        zaak_model_2.zaaktype = factory(ZaakType, zaaktype)

        zaak_document_1 = self.create_zaak_document(zaak_model_1)
        zaak_document_2 = self.create_zaak_document(zaak_model_2)

        user = SuperUserFactory.create()
        rol_1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak_1["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": f"{AssigneeTypeChoices.user}:{user}",
            },
        }
        rol_2 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak_2["url"],
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
        zaak_document_1.rollen = [create_rol_document(factory(Rol, rol_1))]
        zaak_document_2.rollen = [create_rol_document(factory(Rol, rol_2))]
        zaak_document_1.save()
        zaak_document_2.save()
        self.refresh_index()

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(zaak_1["url"], json=zaak_1)
        m.get(zaak_2["url"], json=zaak_2)
        self.client.force_authenticate(user=user)
        with patch(
            "zac.core.services.get_zaaktypen",
            return_value=[factory(ZaakType, zaaktype)],
        ):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        urls = [result["url"] for result in data["results"]]
        self.assertEqual(urls[0], zaak_2["url"])
        self.assertEqual(urls[1], zaak_1["url"])

    def test_cases_ordering_endpoint(self, m, *mocks):
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}/catalogussen/c25a4e4b-c19c-4ab9-a51b-1e9a65890383",
        )

        zaak_1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            startdatum="2021-02-12",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
            zaaktype=zaaktype["url"],
        )
        zaak_model_1 = factory(Zaak, zaak_1)
        zaak_model_1.zaaktype = factory(ZaakType, zaaktype)

        zaak_2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e39-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0011",
            bronorganisatie="123456782",
            startdatum="2021-02-13",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
            zaaktype=zaaktype["url"],
        )
        zaak_model_2 = factory(Zaak, zaak_2)
        zaak_model_2.zaaktype = factory(ZaakType, zaaktype)

        zaak_document_1 = self.create_zaak_document(zaak_model_1)
        zaak_document_2 = self.create_zaak_document(zaak_model_2)

        user = SuperUserFactory.create()
        rol_1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak_1["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": f"{AssigneeTypeChoices.user}:{user}",
            },
        }
        rol_2 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak_2["url"],
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
        zaak_document_1.rollen = [create_rol_document(factory(Rol, rol_1))]
        zaak_document_2.rollen = [create_rol_document(factory(Rol, rol_2))]
        zaak_document_1.save()
        zaak_document_2.save()
        self.refresh_index()

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(zaak_1["url"], json=zaak_1)
        m.get(zaak_2["url"], json=zaak_2)

        # Order on ascending startdatum
        self.client.force_authenticate(user=user)
        with patch(
            "zac.core.services.get_zaaktypen",
            return_value=[factory(ZaakType, zaaktype)],
        ):
            response = self.client.get(self.endpoint + "?ordering=startdatum")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        urls = [result["url"] for result in data["results"]]
        self.assertEqual(urls[0], zaak_1["url"])
        self.assertEqual(urls[1], zaak_2["url"])

        # Order on descending startdatum
        with patch(
            "zac.core.services.get_zaaktypen",
            return_value=[factory(ZaakType, zaaktype)],
        ):
            response = self.client.get(self.endpoint + "?ordering=-startdatum")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        urls = [result["url"] for result in data["results"]]
        self.assertEqual(urls[0], zaak_2["url"])
        self.assertEqual(urls[1], zaak_1["url"])
