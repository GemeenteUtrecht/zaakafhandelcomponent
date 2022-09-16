from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import BlueprintPermissionFactory, UserFactory
from zac.core.permissions import (
    zaken_add_relations,
    zaken_geforceerd_bijwerken,
    zaken_inzien,
)
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zgw.models.zrc import Zaak


@requests_mock.Mocker()
class GetZakenTests(ESMixin, ClearCachesMixin, APITransactionTestCase):
    endpoint = reverse_lazy("zaken-search")

    def test_login_required(self, m):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_query_parameter_errors(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_request_without_permissions(self, m, *mocks):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        # Set up catalogus mocks
        catalogus_root = "http://catalogus.nl/api/v1/"
        catalogus_url = (
            f"{catalogus_root}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )

        Service.objects.create(api_type=APITypes.ztc, api_root=catalogus_root)
        mock_service_oas_get(m, catalogus_root, "ztc")

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{catalogus_root}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        m.get(
            url=f"{catalogus_root}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zaaktype],
            },
        )

        # Set up zaken mocks
        zaken_root = "http://zaken.nl/api/v1/"
        zaak_identificatie = "ZAAK-2020-01"
        Service.objects.create(api_type=APITypes.zrc, api_root=zaken_root)
        mock_service_oas_get(m, zaken_root, "zrc")

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaken_root}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie=zaak_identificatie,
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        zaak["zaaktype"] = factory(ZaakType, zaaktype)
        zaak_model = factory(Zaak, zaak)
        zaak_document = self.create_zaak_document(zaak_model)
        zaak_document.zaaktype = self.create_zaaktype_document(zaak_model.zaaktype)
        zaak_document.save()
        self.refresh_index()

        response = self.client.get(self.endpoint, {"identificatie": zaak_identificatie})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 0)

    def test_valid_request_with_permissions(self, m, *mocks):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        # Set up catalogus mocks
        catalogus_root = "http://catalogus.nl/api/v1/"
        catalogus_url = (
            f"{catalogus_root}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{catalogus_root}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )

        # Set up zaken mocks
        zaken_root = "http://zaken.nl/api/v1/"
        zaak_identificatie = "ZAAK-2020-01"

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaken_root}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie=zaak_identificatie,
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        zaak["zaaktype"] = factory(ZaakType, zaaktype)
        zaak_model = factory(Zaak, zaak)
        zaak_document = self.create_zaak_document(zaak_model)
        zaak_document.zaaktype = self.create_zaaktype_document(zaak_model.zaaktype)
        zaak_document.save()
        self.refresh_index()

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": catalogus_url,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )

        response = self.client.get(self.endpoint, {"identificatie": zaak_identificatie})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["identificatie"], zaak_identificatie)


@requests_mock.Mocker()
class CreateZakenRelationTests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy("add-zaak-relation")

    def test_login_required(self, m):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_query_parameter_errors(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_request_no_permissions(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        response = self.client.post(
            self.endpoint,
            data={
                "relation_zaak": "http://zaken.nl/api/v1/zaken/8d305721-15c9-4b1a-bfac-d2cd52a318d7",
                "main_zaak": "http://zaken.nl/api/v1/zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
                "aard_relatie": "vervolg",
                "aard_relatie_omgekeerde_richting": "onderwerp",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_request_without_permissions_to_relate(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        # Give permissions to the zaken, but not to create relations
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": "http://catalogus.nl/api/v1/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )

        response = self.client.post(
            self.endpoint,
            data={
                "relation_zaak": "http://zaken.nl/api/v1/zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
                "main_zaak": "http://zaken.nl/api/v1/zaken/8d305721-15c9-4b1a-bfac-d2cd52a318d7",
                "aard_relatie": "vervolg",
                "aard_relatie_omgekeerde_richting": "onderwerp",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_request_with_permissions(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        # Mock zaaktype
        catalogus_root = "http://catalogus.nl/api/v1/"
        catalogus_url = (
            f"{catalogus_root}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        Service.objects.create(api_type=APITypes.ztc, api_root=catalogus_root)
        mock_service_oas_get(m, catalogus_root, "ztc")

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{catalogus_root}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )

        m.get(zaaktype["url"], json=zaaktype)

        # Mock zaak
        zaak_root = "http://zaken.nl/api/v1/"

        Service.objects.create(api_type=APITypes.zrc, api_root=zaak_root)
        mock_service_oas_get(m, zaak_root, "zrc")

        main_zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak_root}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            einddatum=None,
        )
        m.get(url=main_zaak["url"], json=main_zaak)

        relation_zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak_root}zaken/8d305721-15c9-4b1a-bfac-d2cd52a318d7",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            einddatum=None,
        )
        m.get(url=relation_zaak["url"], json=relation_zaak)

        # Mock the update of the main zaak
        main_zaak["relevanteAndereZaken"].append(
            {
                "url": relation_zaak["url"],
                "aardRelatie": "vervolg",
            }
        )
        m.patch(url=main_zaak["url"], json=main_zaak)

        # Mock the update of the related zaak
        relation_zaak["relevanteAndereZaken"].append(
            {
                "url": main_zaak["url"],
                "aardRelatie": "onderwerp",
            }
        )
        m.patch(url=relation_zaak["url"], json=relation_zaak)

        # Give permissions to the user
        for permission_name in [zaken_inzien.name, zaken_add_relations.name]:
            BlueprintPermissionFactory.create(
                role__permissions=[permission_name],
                for_user=user,
                policy={
                    "catalogus": catalogus_url,
                    "zaaktype_omschrijving": "ZT1",
                    "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
                },
            )

        response = self.client.post(
            self.endpoint,
            data={
                "relation_zaak": relation_zaak["url"],
                "main_zaak": main_zaak["url"],
                "aard_relatie": "vervolg",
                "aard_relatie_omgekeerde_richting": "onderwerp",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_valid_request_with_permissions_main_zaak_is_closed(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        # Mock zaaktype
        catalogus_root = "http://catalogus.nl/api/v1/"
        catalogus_url = (
            f"{catalogus_root}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        Service.objects.create(api_type=APITypes.ztc, api_root=catalogus_root)
        mock_service_oas_get(m, catalogus_root, "ztc")

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{catalogus_root}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )

        m.get(zaaktype["url"], json=zaaktype)

        # Mock zaak
        zaak_root = "http://zaken.nl/api/v1/"

        Service.objects.create(api_type=APITypes.zrc, api_root=zaak_root)
        mock_service_oas_get(m, zaak_root, "zrc")

        main_zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak_root}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            einddatum="2020-01-01",
        )
        m.get(url=main_zaak["url"], json=main_zaak)

        relation_zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak_root}zaken/8d305721-15c9-4b1a-bfac-d2cd52a318d7",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            einddatum=None,
        )
        m.get(url=relation_zaak["url"], json=relation_zaak)

        # Mock the update of the main zaak
        main_zaak["relevanteAndereZaken"].append(
            {
                "url": relation_zaak["url"],
                "aardRelatie": "vervolg",
            }
        )
        m.patch(url=main_zaak["url"], json=main_zaak)

        # Mock the update of the related zaak
        relation_zaak["relevanteAndereZaken"].append(
            {
                "url": main_zaak["url"],
                "aardRelatie": "onderwerp",
            }
        )
        m.patch(url=relation_zaak["url"], json=relation_zaak)

        # Give permissions to the user
        for permission_name in [zaken_inzien.name, zaken_add_relations.name]:
            BlueprintPermissionFactory.create(
                role__permissions=[permission_name],
                for_user=user,
                policy={
                    "catalogus": catalogus_url,
                    "zaaktype_omschrijving": "ZT1",
                    "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
                },
            )

        response = self.client.post(
            self.endpoint,
            data={
                "relation_zaak": relation_zaak["url"],
                "main_zaak": main_zaak["url"],
                "aard_relatie": "vervolg",
                "aard_relatie_omgekeerde_richting": "onderwerp",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_request_with_permissions_bijdrage_zaak_is_closed(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        # Mock zaaktype
        catalogus_root = "http://catalogus.nl/api/v1/"
        catalogus_url = (
            f"{catalogus_root}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        Service.objects.create(api_type=APITypes.ztc, api_root=catalogus_root)
        mock_service_oas_get(m, catalogus_root, "ztc")

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{catalogus_root}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )

        m.get(zaaktype["url"], json=zaaktype)

        # Mock zaak
        zaak_root = "http://zaken.nl/api/v1/"

        Service.objects.create(api_type=APITypes.zrc, api_root=zaak_root)
        mock_service_oas_get(m, zaak_root, "zrc")

        main_zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak_root}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            einddatum=None,
        )
        m.get(url=main_zaak["url"], json=main_zaak)

        relation_zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak_root}zaken/8d305721-15c9-4b1a-bfac-d2cd52a318d7",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            einddatum="2020-01-01",
        )
        m.get(url=relation_zaak["url"], json=relation_zaak)

        # Mock the update of the main zaak
        main_zaak["relevanteAndereZaken"].append(
            {
                "url": relation_zaak["url"],
                "aardRelatie": "vervolg",
            }
        )
        m.patch(url=main_zaak["url"], json=main_zaak)

        # Mock the update of the related zaak
        relation_zaak["relevanteAndereZaken"].append(
            {
                "url": main_zaak["url"],
                "aardRelatie": "onderwerp",
            }
        )
        m.patch(url=relation_zaak["url"], json=relation_zaak)

        # Give permissions to the user
        for permission_name in [zaken_inzien.name, zaken_add_relations.name]:
            BlueprintPermissionFactory.create(
                role__permissions=[permission_name],
                for_user=user,
                policy={
                    "catalogus": catalogus_url,
                    "zaaktype_omschrijving": "ZT1",
                    "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
                },
            )

        response = self.client.post(
            self.endpoint,
            data={
                "relation_zaak": relation_zaak["url"],
                "main_zaak": main_zaak["url"],
                "aard_relatie": "vervolg",
                "aard_relatie_omgekeerde_richting": "onderwerp",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_request_with_permissions_bijdrage_zaak_is_closed(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        # Mock zaaktype
        catalogus_root = "http://catalogus.nl/api/v1/"
        catalogus_url = (
            f"{catalogus_root}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        Service.objects.create(api_type=APITypes.ztc, api_root=catalogus_root)
        mock_service_oas_get(m, catalogus_root, "ztc")

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{catalogus_root}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )

        m.get(zaaktype["url"], json=zaaktype)

        # Mock zaak
        zaak_root = "http://zaken.nl/api/v1/"

        Service.objects.create(api_type=APITypes.zrc, api_root=zaak_root)
        mock_service_oas_get(m, zaak_root, "zrc")

        main_zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak_root}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            einddatum="2020-01-01",
        )
        m.get(url=main_zaak["url"], json=main_zaak)

        relation_zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak_root}zaken/8d305721-15c9-4b1a-bfac-d2cd52a318d7",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            einddatum="2020-01-01",
        )
        m.get(url=relation_zaak["url"], json=relation_zaak)

        # Mock the update of the main zaak
        main_zaak["relevanteAndereZaken"].append(
            {
                "url": relation_zaak["url"],
                "aardRelatie": "vervolg",
            }
        )
        m.patch(url=main_zaak["url"], json=main_zaak)

        # Mock the update of the related zaak
        relation_zaak["relevanteAndereZaken"].append(
            {
                "url": main_zaak["url"],
                "aardRelatie": "onderwerp",
            }
        )
        m.patch(url=relation_zaak["url"], json=relation_zaak)

        # Give permissions to the user
        for permission_name in [
            zaken_inzien.name,
            zaken_add_relations.name,
            zaken_geforceerd_bijwerken.name,
        ]:
            BlueprintPermissionFactory.create(
                role__permissions=[permission_name],
                for_user=user,
                policy={
                    "catalogus": catalogus_url,
                    "zaaktype_omschrijving": "ZT1",
                    "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
                },
            )

        response = self.client.post(
            self.endpoint,
            data={
                "relation_zaak": relation_zaak["url"],
                "main_zaak": main_zaak["url"],
                "aard_relatie": "vervolg",
                "aard_relatie_omgekeerde_richting": "onderwerp",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_relate_zaak_to_itself(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        zaak_root = "http://zaken.nl/api/v1/"

        response = self.client.post(
            self.endpoint,
            data={
                "relation_zaak": f"{zaak_root}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",  # Relate the zaak to itself
                "main_zaak": f"{zaak_root}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
                "aard_relatie": "vervolg",
                "aard_relatie_omgekeerde_richting": "onderwerp",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
