import contextlib
from unittest.mock import patch

from django.urls import reverse, reverse_lazy

import requests_mock
from django_webtest import TransactionWebTest
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import (
    AccessRequestFactory,
    PermissionSetFactory,
    UserFactory,
)
from zac.core.permissions import zaken_handle_access, zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import (
    generate_oas_component,
    mock_service_oas_get,
    paginated_response,
)

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-001"


@contextlib.contextmanager
def mock_dashboard_context():
    m_get_camunda_user_tasks = patch(
        "zac.werkvoorraad.views.get_camunda_user_tasks", return_value=[]
    )
    m_get_camunda_user_tasks.start()
    m_get_behandelaar_zaken_unfinished = patch(
        "zac.werkvoorraad.views.get_behandelaar_zaken_unfinished", return_value=[]
    )
    m_get_behandelaar_zaken_unfinished.start()
    yield
    m_get_camunda_user_tasks.stop()
    m_get_behandelaar_zaken_unfinished.stop()


@requests_mock.Mocker()
class AccessRequestsTabTests(ClearCachesMixin, TransactionWebTest):
    url = reverse_lazy("index")

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            identificatie="ZT1",
            catalogus=f"{CATALOGI_ROOT}/catalogussen/c25a4e4b-c19c-4ab9-a51b-1e9a65890383",
        )
        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/c25a4e4b-c19c-4ab9-a51b-1e9a65890383",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=self.zaaktype["url"],
        )

        self.access_request1 = AccessRequestFactory.create(zaak=self.zaak["url"])
        self.access_request2 = AccessRequestFactory.create()

        self.app.set_user(self.user)

    def _setUpMocks(self, m):
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype]),
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?zaaktype={self.zaaktype['url']}"
            "&maximaleVertrouwelijkheidaanduiding=zeer_geheim"
            f"&rol__betrokkeneIdentificatie__medewerker__identificatie={self.user.username}"
            "&rol__omschrijvingGeneriek=behandelaar"
            "&rol__betrokkeneType=medewerker",
            json=paginated_response([self.zaak]),
        )

    def test_display_access_requests_no_handle_permission(self, m):
        self._setUpMocks(m)

        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        # mock out all the other calls - we're testing access request part here
        with mock_dashboard_context():
            response = self.app.get(self.url)

        self.assertEqual(response.status_code, 200)

        list_items = response.html.find(id="work-access-requests").ul.find_all(
            "li", recursive=False
        )
        self.assertEqual(len(list_items), 0)

    def test_display_access_requests_with_handle_permission(self, m):
        self._setUpMocks(m)

        PermissionSetFactory.create(
            permissions=[zaken_inzien.name, zaken_handle_access.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        # mock out all the other calls - we're testing access request part here
        with mock_dashboard_context():
            response = self.app.get(self.url)

        self.assertEqual(response.status_code, 200)

        list_items = response.html.find(id="work-access-requests").ul.find_all(
            "li", recursive=False
        )
        self.assertEqual(len(list_items), 1)

        list_item = list_items[0]
        zaak_url = list_item.a["href"]
        self.assertEqual(
            zaak_url,
            reverse("core:zaak-access-requests", args=[BRONORGANISATIE, IDENTIFICATIE]),
        )

        requesters = list_item.find_all("li")
        self.assertEqual(len(requesters), 1)
        self.assertEqual(requesters[0].text, self.access_request1.requester.username)
