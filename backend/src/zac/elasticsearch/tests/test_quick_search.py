from unittest.mock import MagicMock

from django.conf import settings
from django.urls import reverse_lazy

from elasticsearch_dsl import Index
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.accounts.datastructures import VA_ORDER
from zac.accounts.tests.factories import (
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import create_related_zaak_document
from zac.elasticsearch.tests.utils import ESMixin

from ..documents import (
    InformatieObjectDocument,
    ObjectDocument,
    ZaakDocument,
    ZaakTypeDocument,
)
from ..searches import quick_search
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


class QuickSearchTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    endpoint = reverse_lazy("quick-search")

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

    def setUp(self) -> None:
        super().setUp()
        self.zaaktype_document1 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            omschrijving="zaaktype1",
        )
        self.zaak_document1 = ZaakDocument(
            meta={"id": "a522d30c-6c10-47fe-82e3-e9f524c14ca8"},
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=self.zaaktype_document1,
            identificatie="ZAAK-2022-0000001010",
            bronorganisatie="123456",
            omschrijving="Some zaak description",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            va_order=VA_ORDER[VertrouwelijkheidsAanduidingen.openbaar],
            rollen=[
                {
                    "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
                    "betrokkene_type": "organisatorische_eenheid",
                    "betrokkene_identificatie": {
                        "identificatie": "123456",
                    },
                },
                {
                    "url": f"{ZAKEN_ROOT}rollen/de7039d7-242a-4186-91c3-c3b49228211a",
                    "betrokkene_type": "medewerker",
                    "omschrijving_generiek": "behandelaar",
                    "betrokkene_identificatie": {
                        "identificatie": f"{AssigneeTypeChoices.user}:some_username",
                    },
                },
            ],
            eigenschappen={
                "tekst": {
                    "Beleidsveld": "Asiel en Integratie",
                    "Bedrag incl  BTW": "aaa",
                }
            },
            deadline="2021-12-31",
        )
        self.zaak_document1.save()
        self.zaaktype_document2 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/de7039d7-242a-4186-91c3-c3b49228211a",
            catalogus=f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            omschrijving="zaaktype2",
        )
        self.zaak_document2 = ZaakDocument(
            meta={"id": "a8c8bc90-defa-4548-bacd-793874c013ab"},
            url="https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013ab",
            zaaktype=self.zaaktype_document2,
            identificatie="ZAAK-2021-000000105",
            bronorganisatie="7890",
            omschrijving="een omschrijving",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            va_order=VA_ORDER[VertrouwelijkheidsAanduidingen.zaakvertrouwelijk],
            rollen=[],
            eigenschappen={"tekst": {"Beleidsveld": "Integratie"}},
            deadline="2021-12-31",
        )
        self.zaak_document2.save()

        related_zaak_1 = create_related_zaak_document(self.zaak_document1)
        self.object_document_1 = ObjectDocument(
            url="some-keywoird",
            object_type="https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013ab",
            record_data={"some-field": "some omschrijving value"},
            related_zaken=[related_zaak_1],
        )
        self.object_document_1.save()

        related_zaak_2 = create_related_zaak_document(self.zaak_document2)
        self.eio_document_1 = InformatieObjectDocument(
            url="some-keyword",
            titel="some-titel_omsch_2022-20105.pdf(1)",
            related_zaken=[related_zaak_2],
        )
        self.eio_document_1.save()
        self.eio_document_2 = InformatieObjectDocument(
            url="some-keyword",
            titel="test.txt",
            related_zaken=[],
        )
        self.eio_document_2.save()

        self.refresh_index()

    def test_quick_search(self):
        results = quick_search("test.txt")
        self.assertEqual(
            len(results["zaken"]),
            0,
        )
        self.assertEqual(results["documenten"][0].url, self.eio_document_2.url)
        self.assertEqual(
            len(results["objecten"]),
            0,
        )

        results = quick_search("2022 omsch")
        self.assertEqual(
            results["zaken"][0].identificatie, self.zaak_document1.identificatie
        )
        self.assertEqual(results["objecten"][0].url, self.object_document_1.url)
        self.assertEqual(results["documenten"][0].url, self.eio_document_1.url)

        results = quick_search("2022")
        self.assertEqual(
            results["zaken"][0].identificatie, self.zaak_document1.identificatie
        )
        self.assertEqual(len(results["objecten"]), 0)
        self.assertEqual(results["documenten"][0].url, self.eio_document_1.url)

        results = quick_search("2021")
        self.assertEqual(
            results["zaken"][0].identificatie, self.zaak_document2.identificatie
        )
        self.assertEqual(len(results["objecten"]), 0)
        self.assertEqual(len(results["documenten"]), 0)

        results = quick_search("2021 omsch")
        self.assertEqual(
            results["zaken"][0].identificatie, self.zaak_document2.identificatie
        )
        self.assertEqual(results["objecten"][0].url, self.object_document_1.url)
        self.assertEqual(results["documenten"][0].url, self.eio_document_1.url)

    def test_quick_search_blueprint_permissions(self):
        user = UserFactory.create()
        request = MagicMock()
        request.user = user
        request.auth = None

        results = quick_search("2022 omsch", only_allowed=True, request=request)
        self.assertEqual(len(results["zaken"]), 0)
        self.assertEqual(len(results["objecten"]), 0)
        self.assertEqual(len(results["documenten"]), 0)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            policy={
                "catalogus": self.zaaktype_document1.catalogus,
                "zaaktype_omschrijving": self.zaaktype_document1.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            for_user=user,
        )

        results = quick_search("2022 omsch", only_allowed=True, request=request)
        self.assertEqual(
            results["zaken"][0].identificatie, self.zaak_document1.identificatie
        )
        self.assertEqual(results["objecten"][0].url, self.object_document_1.url)
        # Document isn't allowed to be returned because of the lack of
        # blueprint permissions for zaaktype 2.
        self.assertEqual(len(results["documenten"]), 0)

        # Now add appropriate blueprint permission for zaaktype 2
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            policy={
                "catalogus": self.zaaktype_document2.catalogus,
                "zaaktype_omschrijving": self.zaaktype_document2.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            for_user=user,
        )
        results = quick_search("2022 omsch", only_allowed=True, request=request)

        self.assertEqual(results["documenten"][0].url, self.eio_document_1.url)

    def test_quick_search_atomic_permissions_for_zaak(self):
        user = UserFactory.create()
        request = MagicMock()
        request.user = user
        request.auth = None

        results = quick_search("2022 omsch", only_allowed=True, request=request)
        self.assertEqual(len(results["zaken"]), 0)
        self.assertEqual(len(results["objecten"]), 0)
        self.assertEqual(len(results["documenten"]), 0)

        AtomicPermissionFactory.create(
            permission=zaken_inzien.name,
            object_url=self.zaak_document1.url,
            for_user=user,
        )

        results = quick_search("2022 omsch", only_allowed=True, request=request)
        self.assertEqual(
            results["zaken"][0].identificatie, self.zaak_document1.identificatie
        )
        self.assertEqual(results["objecten"][0].url, self.object_document_1.url)
        # Document isn't allowed to be returned because of the lack of
        # atomic permissions for zaak 2.
        self.assertEqual(len(results["documenten"]), 0)

        AtomicPermissionFactory.create(
            permission=zaken_inzien.name,
            object_url=self.zaak_document2.url,
            for_user=user,
        )

        results = quick_search("2022 omsch", only_allowed=True, request=request)
        self.assertEqual(results["documenten"][0].url, self.eio_document_1.url)

    def test_quick_search_endpoint_superuser(self):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.post(self.endpoint, {"search": "2022 omsch"})
        self.assertEqual(response.status_code, 200)

        results = response.json()
        self.assertEqual(
            results["zaken"][0]["identificatie"], self.zaak_document1.identificatie
        )
        self.assertEqual(
            results["objecten"][0]["recordData"], self.object_document_1.record_data
        )
        self.assertEqual(results["documenten"][0]["titel"], self.eio_document_1.titel)

    def test_quick_search_endpoint_not_authenticated(self):
        response = self.client.post(self.endpoint, {"search": "2022 omsch"})
        self.assertEqual(response.status_code, 403)

    def test_quick_search_endpoint_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.post(self.endpoint, {"search": "2022 omsch"})
        self.assertEqual(response.status_code, 200)

        results = response.json()
        self.assertEqual(len(results["zaken"]), 0)
        self.assertEqual(len(results["objecten"]), 0)
        self.assertEqual(len(results["documenten"]), 0)
