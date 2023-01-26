from unittest.mock import MagicMock

from django.conf import settings
from django.test import TestCase

from elasticsearch_dsl import Index
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.accounts.tests.factories import (
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.permissions import zaken_inzien

from ..documents import ZaakDocument, ZaakTypeDocument
from ..searches import search_zaken
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


class SearchZakenTests(ESMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.zaaktype_document1 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            omschrijving="zaaktype1",
            identificatie="id1",
        )
        self.zaak_document1 = ZaakDocument(
            meta={"id": "a522d30c-6c10-47fe-82e3-e9f524c14ca8"},
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=self.zaaktype_document1,
            identificatie="ZAAK1",
            bronorganisatie="123456",
            omschrijving="Some zaak description",
            vertrouwelijkheidaanduiding="beperkt_openbaar",
            va_order=16,
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
            identificatie="id2",
        )
        self.zaak_document2 = ZaakDocument(
            meta={"id": "a8c8bc90-defa-4548-bacd-793874c013ab"},
            url="https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013ab",
            zaaktype=self.zaaktype_document2,
            identificatie="ZAAK2",
            bronorganisatie="7890",
            omschrijving="Other description",
            vertrouwelijkheidaanduiding="confidentieel",
            va_order=20,
            rollen=[],
            eigenschappen={"tekst": {"Beleidsveld": "Integratie"}},
            deadline="2021-12-31",
        )
        self.zaak_document2.save()

        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.refresh()

    def test_search_zaaktype(self):
        result = search_zaken(
            zaaktypen=[
                "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa"
            ],
            only_allowed=False,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_identificatie(self):
        result = search_zaken(identificatie="ZAAK1", only_allowed=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_bronorg(self):
        result = search_zaken(bronorganisatie="123456", only_allowed=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_behandelaar(self):
        result = search_zaken(behandelaar="some_username", only_allowed=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_only_allowed_blueprint(self):
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            policy={
                "catalogus": f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                "zaaktype_omschrijving": "zaaktype1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            for_user=user,
        )
        request = MagicMock()
        request.user = user
        request.auth = None
        result = search_zaken(request=request, only_allowed=True)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_only_allowed_atomic(self):
        user = UserFactory.create()
        AtomicPermissionFactory.create(
            object_url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            permission=zaken_inzien.name,
            for_user=user,
        )
        request = MagicMock()
        request.user = user
        request.auth = None
        result = search_zaken(request=request, only_allowed=True)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_omschrijving(self):
        result = search_zaken(omschrijving="some", only_allowed=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_omschrijving_part(self):
        result = search_zaken(omschrijving="som", only_allowed=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_eigenschappen(self):
        result = search_zaken(
            eigenschappen={"Beleidsveld": "Asiel\ en\ Integratie"}, only_allowed=False
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_partial_eigenschappen(self):
        result = search_zaken(eigenschappen={"Beleidsveld": "en"}, only_allowed=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_search_eigenschappen_with_point(self):
        result = search_zaken(
            eigenschappen={"Bedrag incl. BTW": "aaa"}, only_allowed=False
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_combined(self):
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            policy={
                "catalogus": f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                "zaaktype_omschrijving": "zaaktype1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            for_user=user,
        )
        request = MagicMock()
        request.user = user
        result = search_zaken(
            request=request,
            zaaktypen=[
                "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa"
            ],
            bronorganisatie="123456",
            identificatie="ZAAK1",
            omschrijving="some",
            eigenschappen={"Beleidsveld": "Asiel"},
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, self.zaak_document1.url)

    def test_ordering(self):
        super_user = SuperUserFactory.create()
        request = MagicMock()
        request.user = super_user
        result = search_zaken(request=request, ordering=("-identificatie.keyword",))
        self.assertEqual(result[0].url, self.zaak_document2.url)

    def test_nested_ordering(self):
        super_user = SuperUserFactory.create()
        request = MagicMock()
        request.user = super_user
        result = search_zaken(request=request, ordering=("-zaaktype.omschrijving",))
        self.assertEqual(result[0].url, self.zaak_document2.url)
