import uuid

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import SuperUserFactory

from ..constants import BoardObjectTypes
from ..models import BoardItem
from .factories import BoardColumnFactory, BoardItemFactory

ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/482de5b2-4779-4b29-b84f-add888352182"


class BoardItemAPITests(APITestCase):
    def setUp(self):
        super().setUp()

        self.user = SuperUserFactory.create()
        self.client.force_authenticate(user=self.user)

    def test_list_items(self):
        item1 = BoardItemFactory.create(column__name="wip")
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
                    "board": f"http://testserver{reverse('board-detail', args=[item2.column.board.uuid])}",
                    "column": {
                        "uuid": str(item2.column.uuid),
                        "name": "done",
                        "slug": "done",
                        "order": item2.column.order,
                        "created": item2.column.created.isoformat()[:-6] + "Z",
                        "modified": item2.column.modified.isoformat()[:-6] + "Z",
                    },
                },
                {
                    "url": f"http://testserver{reverse('boarditem-detail', args=[item1.uuid])}",
                    "uuid": str(item1.uuid),
                    "objectType": "zaak",
                    "object": item1.object,
                    "board": f"http://testserver{reverse('board-detail', args=[item1.column.board.uuid])}",
                    "column": {
                        "uuid": str(item1.column.uuid),
                        "name": "wip",
                        "slug": "wip",
                        "order": item1.column.order,
                        "created": item1.column.created.isoformat()[:-6] + "Z",
                        "modified": item1.column.modified.isoformat()[:-6] + "Z",
                    },
                },
            ],
        )

    def test_list_items_filter_on_board_uuid(self):
        item = BoardItemFactory.create()
        BoardItemFactory.create()
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
        item = BoardItemFactory.create(column__board__slug="scrum")
        BoardItemFactory.create()
        url = reverse("boarditem-list")

        response = self.client.get(url, {"board_slug": "scrum"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"],
            f"http://testserver{reverse('boarditem-detail', args=[item.uuid])}",
        )

    def test_retrieve_item(self):
        item = BoardItemFactory.create()
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
                "board": f"http://testserver{reverse('board-detail', args=[item.column.board.uuid])}",
                "column": {
                    "uuid": str(item.column.uuid),
                    "name": item.column.name,
                    "slug": item.column.slug,
                    "order": item.column.order,
                    "created": item.column.created.isoformat()[:-6] + "Z",
                    "modified": item.column.modified.isoformat()[:-6] + "Z",
                },
            },
        )

    def test_create_item_success(self):
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
            response.json(), {"nonFieldErrors": ["This object is already on the board"]}
        )

    def test_update_item_column_success(self):
        old_col = BoardColumnFactory.create()
        new_col = BoardColumnFactory.create(board=old_col.board)
        item = BoardItemFactory.create(column=old_col)
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.patch(url, {"column_uuid": str(new_col.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item.refresh_from_db()

        self.assertEqual(item.column, new_col)

    def test_update_item_change_column_from_another_board(self):
        old_col, new_col = BoardColumnFactory.create_batch(2)
        item = BoardItemFactory.create(column=old_col)
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.patch(url, {"column_uuid": str(new_col.uuid)})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(), {"columnUuid": ["The board of the item can't be changed"]}
        )

    def test_update_item_change_object(self):
        item = BoardItemFactory.create()
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.patch(url, {"object": ZAAK_URL})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"object": ["This field can't be changed."]})

    def test_delete_item_success(self):
        item = BoardItemFactory.create()
        url = reverse("boarditem-detail", args=[item.uuid])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(BoardItem.objects.count(), 0)
