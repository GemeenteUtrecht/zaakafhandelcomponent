from unittest.mock import MagicMock

from django.test import TestCase

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
from zac.elasticsearch.tests.utils import ESMixin

from ..documents import ZaakDocument, ZaakTypeDocument
from ..searches import count_by_zaaktype
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


class CountByZaakTypeTests(ClearCachesMixin, ESMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.zaaktype_document1 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            omschrijving="zaaktype1",
            identificatie="zaaktype1",
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
            identificatie="zaaktype2",
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
        self.refresh_index()

    def test_count_by_zaaktype_no_permissions(self):
        user = UserFactory.create()
        request = MagicMock()
        request.user = user
        request.auth = None
        results = count_by_zaaktype(request=request)
        self.assertEqual(results, [])

    def test_count_by_zaaktype_blueprint_permissions(self):
        user = UserFactory.create()
        request = MagicMock()
        request.user = user
        request.auth = None

        results = count_by_zaaktype(request=request)
        self.assertEqual(results, [])

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            policy={
                "catalogus": self.zaaktype_document1.catalogus,
                "zaaktype_omschrijving": self.zaaktype_document1.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            for_user=user,
        )

        results = count_by_zaaktype(request=request)
        self.assertEqual(
            results[0].key,
            "https://api.catalogi.nl/api/v1/catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        )
        self.assertEqual(results[0].doc_count, 1)
        self.assertEqual(results[0].child.buckets[0].key, "zaaktype1")
        self.assertEqual(results[0].child.buckets[0].doc_count, 1)

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
        results = count_by_zaaktype(request=request)
        self.assertEqual(
            results[0].key,
            "https://api.catalogi.nl/api/v1/catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        )
        self.assertEqual(results[0].doc_count, 2)
        self.assertTrue(len(results[0].child.buckets) == 2)

    def test_count_by_zaaktype_atomic_permissions_for_zaak(self):
        user = UserFactory.create()
        request = MagicMock()
        request.user = user
        request.auth = None

        results = count_by_zaaktype(request=request)
        self.assertEqual(results, [])

        AtomicPermissionFactory.create(
            permission=zaken_inzien.name,
            object_url=self.zaak_document1.url,
            for_user=user,
        )
        results = count_by_zaaktype(request=request)
        self.assertEqual(
            results[0].key,
            "https://api.catalogi.nl/api/v1/catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        )
        self.assertEqual(results[0].doc_count, 1)
        self.assertEqual(results[0].child.buckets[0].key, "zaaktype1")
        self.assertEqual(results[0].child.buckets[0].doc_count, 1)

        # Now add appropriate atomic permission for zaaktype 2
        AtomicPermissionFactory.create(
            permission=zaken_inzien.name,
            object_url=self.zaak_document2.url,
            for_user=user,
        )
        results = count_by_zaaktype(request=request)
        self.assertEqual(
            results[0].key,
            "https://api.catalogi.nl/api/v1/catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        )
        self.assertEqual(results[0].doc_count, 2)
        self.assertTrue(len(results[0].child.buckets) == 2)

    def test_count_by_zaaktype_superuser(self):
        user = SuperUserFactory.create()
        request = MagicMock()
        request.user = user
        request.auth = None

        results = count_by_zaaktype(request=request)
        self.assertEqual(
            results[0].key,
            "https://api.catalogi.nl/api/v1/catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        )
        self.assertEqual(results[0].doc_count, 2)
        self.assertTrue(len(results[0].child.buckets) == 2)
