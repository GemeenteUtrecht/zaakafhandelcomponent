import contextlib
from unittest.mock import patch

from django.urls import reverse, reverse_lazy

import requests_mock
from django_webtest import TransactionWebTest
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    AccessRequestFactory,
    PermissionDefinitionFactory,
    UserFactory,
)
from zac.core.permissions import zaken_handle_access, zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

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
    yield
    m_get_camunda_user_tasks.stop()


@requests_mock.Mocker()
class AccessRequestsTabTests(ESMixin, ClearCachesMixin, TransactionWebTest):
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
        zaaktype_object = factory(ZaakType, self.zaaktype)
        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/c25a4e4b-c19c-4ab9-a51b-1e9a65890383",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=self.zaaktype["url"],
        )
        zaak_object = factory(Zaak, self.zaak)
        zaak_object.zaaktype = zaaktype_object
        # can't use generate_oas_component because of polymorphism
        rol = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": self.zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
            },
        }
        self.create_zaak_document(zaak_object)
        self.add_rol_to_document(rol)
        self.refresh_index()
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
        m.get(self.zaak["url"], json=self.zaak)

    def test_display_access_requests_no_handle_permission(self, m):
        self._setUpMocks(m)

        PermissionDefinitionFactory.create(
            permission=[zaken_inzien.name],
            object_url=self.zaak["url"],
            for_user=self.user,
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

        for permission in [zaken_inzien.name, zaken_handle_access.name]:
            PermissionDefinitionFactory.create(
                permission=permission, object_url=self.zaak["url"], for_user=self.user
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
