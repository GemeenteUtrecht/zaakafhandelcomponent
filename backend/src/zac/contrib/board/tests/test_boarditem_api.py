import uuid

from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.datastructures import VA_ORDER
from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaken_geforceerd_bijwerken, zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get
from zgw.models.zrc import Zaak

from ..constants import BoardObjectTypes
from ..models import BoardItem
from .factories import BoardColumnFactory, BoardFactory, BoardItemFactory

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/482de5b2-4779-4b29-b84f-add888352182"


@requests_mock.Mocker()
class BoardItemPermissionTests(ESMixin, ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        # data for ES documents
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=cls.zaaktype["url"],
            identificatie="zaak1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            eigenschappen=[],
        )
        cls.zaaktype_model = factory(ZaakType, cls.zaaktype)
        cls.zaak_model = factory(Zaak, cls.zaak)
        cls.zaak_model.zaaktype = cls.zaaktype_model

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)
        zaak_document = self.create_zaak_document(self.zaak_model)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype_model)
        zaak_document.save()
        self.refresh_index()

    def _setUpMock(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

    def test_list_no_permissions(self, m):
        BoardItemFactory.create(object=ZAAK_URL)
        url = reverse("boarditem-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_list_only_allowed(self, m):
        item = BoardItemFactory.create(object=ZAAK_URL)
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        url = reverse("boarditem-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"],
            f"http://testserver{reverse('boarditem-detail', args=[item.uuid])}",
        )

    def test_retrieve_other_permission(self, m):
        self._setUpMock(m)

        item = BoardItemFactory.create(object=ZAAK_URL)
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_has_permission(self, m):
        self._setUpMock(m)

        item = BoardItemFactory.create(object=ZAAK_URL)
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_other_permission(self, m):
        self._setUpMock(m)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        column = BoardColumnFactory.create()
        url = reverse("boarditem-list")
        data = {"object": ZAAK_URL, "column_uuid": str(column.uuid)}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_has_permission(self, m):
        self._setUpMock(m)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        column = BoardColumnFactory.create()
        url = reverse("boarditem-list")
        data = {"object": ZAAK_URL, "column_uuid": str(column.uuid)}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_has_permission_but_zaak_is_closed(self, m):
        self._setUpMock(m)
        mock_resource_get(m, {**self.zaak, "einddatum": "2020-01-01"})
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        column = BoardColumnFactory.create()
        url = reverse("boarditem-list")
        data = {"object": ZAAK_URL, "column_uuid": str(column.uuid)}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_has_permission_for_closed_zaak(self, m):
        self._setUpMock(m)
        mock_resource_get(m, {**self.zaak, "einddatum": "2020-01-01"})
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        column = BoardColumnFactory.create()
        url = reverse("boarditem-list")
        data = {"object": ZAAK_URL, "column_uuid": str(column.uuid)}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_other_permission(self, m):
        self._setUpMock(m)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        old_col = BoardColumnFactory.create()
        new_col = BoardColumnFactory.create(board=old_col.board)
        item = BoardItemFactory.create(column=old_col, object=ZAAK_URL)
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.patch(url, {"column_uuid": new_col.uuid})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_has_permission(self, m):
        self._setUpMock(m)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        old_col = BoardColumnFactory.create()
        new_col = BoardColumnFactory.create(board=old_col.board)
        item = BoardItemFactory.create(column=old_col, object=ZAAK_URL)
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.patch(url, {"column_uuid": new_col.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_other_permission(self, m):
        self._setUpMock(m)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        item = BoardItemFactory.create(object=ZAAK_URL)
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_has_permission(self, m):
        self._setUpMock(m)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        item = BoardItemFactory.create(object=ZAAK_URL)
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class BoardItemAPITests(ESMixin, ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        cls.user = SuperUserFactory.create()
        # data for ES documents
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=cls.zaaktype["url"],
            identificatie="zaak1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            eigenschappen=[],
        )
        cls.zaaktype_model = factory(ZaakType, cls.zaaktype)
        cls.zaak_model = factory(Zaak, cls.zaak)
        cls.zaak_model.zaaktype = cls.zaaktype_model
        cls.zaak_data = {
            "url": ZAAK_URL,
            "zaaktype": {
                "url": cls.zaaktype_model.url,
                "catalogus": CATALOGUS_URL,
                "omschrijving": "ZT1",
                "identificatie": cls.zaaktype_model.identificatie,
            },
            "identificatie": "zaak1",
            "bronorganisatie": cls.zaak_model.bronorganisatie,
            "omschrijving": cls.zaak_model.omschrijving,
            "vertrouwelijkheidaanduiding": "openbaar",
            "vaOrder": VA_ORDER["openbaar"],
            "rollen": [],
            "startdatum": cls.zaak_model.startdatum.isoformat() + "T00:00:00Z",
            "einddatum": None,
            "registratiedatum": cls.zaak_model.registratiedatum.isoformat()
            + "T00:00:00Z",
            "deadline": cls.zaak_model.deadline.isoformat() + "T00:00:00Z",
            "eigenschappen": [],
            "status": {
                "url": None,
                "statustype": None,
                "datumStatusGezet": None,
                "statustoelichting": None,
            },
            "toelichting": cls.zaak_model.toelichting,
            "zaakinformatieobjecten": [],
            "zaakobjecten": [],
            "zaakgeometrie": None,
        }

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)
        zaak_document = self.create_zaak_document(self.zaak_model)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype_model)
        zaak_document.save()
        self.refresh_index()

    def test_list_items(self):
        item1 = BoardItemFactory.create(column__name="wip", object=ZAAK_URL)
        item2 = BoardItemFactory.create(column__name="done")
        url = reverse("boarditem-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "url": f"http://testserver{reverse('boarditem-detail', args=[item2.uuid])}",
                    "uuid": str(item2.uuid),
                    "objectType": "zaak",
                    "object": item2.object,
                    "board": {
                        "url": f"http://testserver{reverse('board-detail', args=[item2.column.board.uuid])}",
                        "uuid": str(item2.column.board.uuid),
                        "name": item2.column.board.name,
                        "slug": item2.column.board.slug,
                        "created": item2.column.board.created.isoformat()[:-6] + "Z",
                        "modified": item2.column.board.modified.isoformat()[:-6] + "Z",
                        "columns": [
                            {
                                "uuid": str(item2.column.uuid),
                                "name": "done",
                                "slug": "done",
                                "order": item2.column.order,
                                "created": item2.column.created.isoformat()[:-6] + "Z",
                                "modified": item2.column.modified.isoformat()[:-6]
                                + "Z",
                            },
                        ],
                    },
                    "column": {
                        "uuid": str(item2.column.uuid),
                        "name": "done",
                        "slug": "done",
                        "order": item2.column.order,
                        "created": item2.column.created.isoformat()[:-6] + "Z",
                        "modified": item2.column.modified.isoformat()[:-6] + "Z",
                    },
                    "zaak": None,
                },
                {
                    "url": f"http://testserver{reverse('boarditem-detail', args=[item1.uuid])}",
                    "uuid": str(item1.uuid),
                    "objectType": "zaak",
                    "object": item1.object,
                    "board": {
                        "url": f"http://testserver{reverse('board-detail', args=[item1.column.board.uuid])}",
                        "uuid": str(item1.column.board.uuid),
                        "name": item1.column.board.name,
                        "slug": item1.column.board.slug,
                        "created": item1.column.board.created.isoformat()[:-6] + "Z",
                        "modified": item1.column.board.modified.isoformat()[:-6] + "Z",
                        "columns": [
                            {
                                "uuid": str(item1.column.uuid),
                                "name": "wip",
                                "slug": "wip",
                                "order": item1.column.order,
                                "created": item1.column.created.isoformat()[:-6] + "Z",
                                "modified": item1.column.modified.isoformat()[:-6]
                                + "Z",
                            },
                        ],
                    },
                    "column": {
                        "uuid": str(item1.column.uuid),
                        "name": "wip",
                        "slug": "wip",
                        "order": item1.column.order,
                        "created": item1.column.created.isoformat()[:-6] + "Z",
                        "modified": item1.column.modified.isoformat()[:-6] + "Z",
                    },
                    "zaak": self.zaak_data,
                },
            ],
        )

    def test_list_items_filter_on_board_uuid(self):
        item = BoardItemFactory.create(object=ZAAK_URL)
        url = reverse("boarditem-list")

        response = self.client.get(url, {"board_uuid": str(item.column.board.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"],
            f"http://testserver{reverse('boarditem-detail', args=[item.uuid])}",
        )

    def test_list_items_filter_on_board_slug(self):
        item = BoardItemFactory.create(column__board__slug="scrum", object=ZAAK_URL)
        url = reverse("boarditem-list")

        response = self.client.get(url, {"board_slug": "scrum"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"],
            f"http://testserver{reverse('boarditem-detail', args=[item.uuid])}",
        )

    def test_list_items_filter_on_zaak_url(self):
        item = BoardItemFactory.create(object=ZAAK_URL)
        url = reverse("boarditem-list")

        response = self.client.get(url, {"zaakUrl": ZAAK_URL})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"],
            f"http://testserver{reverse('boarditem-detail', args=[item.uuid])}",
        )

    @requests_mock.Mocker()
    def test_retrieve_item(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        board = BoardFactory.create()
        col1, col2 = BoardColumnFactory.create_batch(2, board=board)
        item = BoardItemFactory.create(object=ZAAK_URL, column=col1)
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "url": f"http://testserver{reverse('boarditem-detail', args=[item.uuid])}",
                "uuid": str(item.uuid),
                "objectType": "zaak",
                "object": item.object,
                "board": {
                    "url": f"http://testserver{reverse('board-detail', args=[board.uuid])}",
                    "uuid": str(board.uuid),
                    "name": board.name,
                    "slug": board.slug,
                    "created": board.created.isoformat()[:-6] + "Z",
                    "modified": board.modified.isoformat()[:-6] + "Z",
                    "columns": [
                        {
                            "uuid": str(col1.uuid),
                            "name": col1.name,
                            "slug": col1.slug,
                            "order": col1.order,
                            "created": col1.created.isoformat()[:-6] + "Z",
                            "modified": col1.modified.isoformat()[:-6] + "Z",
                        },
                        {
                            "uuid": str(col2.uuid),
                            "name": col2.name,
                            "slug": col2.slug,
                            "order": col2.order,
                            "created": col2.created.isoformat()[:-6] + "Z",
                            "modified": col2.modified.isoformat()[:-6] + "Z",
                        },
                    ],
                },
                "column": {
                    "uuid": str(col1.uuid),
                    "name": col1.name,
                    "slug": col1.slug,
                    "order": col1.order,
                    "created": col1.created.isoformat()[:-6] + "Z",
                    "modified": col1.modified.isoformat()[:-6] + "Z",
                },
                "zaak": self.zaak_data,
            },
        )

    @requests_mock.Mocker()
    def test_create_item_success(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        url = reverse("boarditem-list")
        column = BoardColumnFactory.create()
        data = {"object": ZAAK_URL, "column_uuid": str(column.uuid)}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BoardItem.objects.count(), 1)

        item = BoardItem.objects.get()

        self.assertEqual(item.column, column)
        self.assertEqual(item.object_type, BoardObjectTypes.zaak)
        self.assertEqual(item.object, ZAAK_URL)

    def test_create_item_column_not_exist(self):
        url = reverse("boarditem-list")
        data = {"object": ZAAK_URL, "column_uuid": str(uuid.uuid4())}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("columnUuid" in response.json())

    def test_create_item_duplicate_object_in_the_board(self):
        url = reverse("boarditem-list")
        item = BoardItemFactory.create(object=ZAAK_URL)
        col = BoardColumnFactory.create(board=item.column.board)

        data = {"object": ZAAK_URL, "column_uuid": str(col.uuid)}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(), {"nonFieldErrors": ["Dit OBJECT staat al op het bord"]}
        )

    @requests_mock.Mocker()
    def test_update_item_column_success(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        old_col = BoardColumnFactory.create()
        new_col = BoardColumnFactory.create(board=old_col.board)
        item = BoardItemFactory.create(column=old_col, object=ZAAK_URL)
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.patch(url, {"column_uuid": str(new_col.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item.refresh_from_db()

        self.assertEqual(item.column, new_col)

    @requests_mock.Mocker()
    def test_update_item_change_column_from_another_board(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        old_col, new_col = BoardColumnFactory.create_batch(2)
        item = BoardItemFactory.create(column=old_col, object=ZAAK_URL)
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.patch(url, {"column_uuid": str(new_col.uuid)})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"columnUuid": ["De bord van het item kan niet worden veranderd"]},
        )

    @requests_mock.Mocker()
    def test_update_item_change_object(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        item = BoardItemFactory.create(object=self.zaak["url"])
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.patch(url, {"object": f"{ZAKEN_ROOT}/zaak/some-zaak"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(), {"object": ["Dit veld kan niet veranderd worden."]}
        )

    @requests_mock.Mocker()
    def test_delete_item_success(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        item = BoardItemFactory.create(object=self.zaak["url"])
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(BoardItem.objects.count(), 0)
