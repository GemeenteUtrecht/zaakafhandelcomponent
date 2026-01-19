from django.urls import reverse, reverse_lazy

from rest_framework import status
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import SuperUserFactory

from .factories import BoardColumnFactory, BoardFactory


class BoardAPITests(APITestCase):
    url = reverse_lazy("board-list")

    def setUp(self):
        super().setUp()

        self.user = SuperUserFactory.create()
        self.client.force_authenticate(user=self.user)

    def test_list_boards(self):
        board1 = BoardFactory.create(name="first")
        column1 = BoardColumnFactory.create(board=board1)
        board2 = BoardFactory.create(name="second")
        column2 = BoardColumnFactory.create(board=board2)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "url": f"http://testserver{reverse('board-detail', args=[board2.uuid])}",
                    "uuid": str(board2.uuid),
                    "name": "second",
                    "slug": "second",
                    "created": board2.created.isoformat()[:-6] + "Z",
                    "modified": board2.modified.isoformat()[:-6] + "Z",
                    "columns": [
                        {
                            "uuid": str(column2.uuid),
                            "name": column2.name,
                            "slug": column2.slug,
                            "order": column2.order,
                            "created": column2.created.isoformat()[:-6] + "Z",
                            "modified": column2.modified.isoformat()[:-6] + "Z",
                        }
                    ],
                },
                {
                    "url": f"http://testserver{reverse('board-detail', args=[board1.uuid])}",
                    "uuid": str(board1.uuid),
                    "name": "first",
                    "slug": "first",
                    "created": board1.created.isoformat()[:-6] + "Z",
                    "modified": board1.modified.isoformat()[:-6] + "Z",
                    "columns": [
                        {
                            "uuid": str(column1.uuid),
                            "name": column1.name,
                            "slug": column1.slug,
                            "order": column1.order,
                            "created": column1.created.isoformat()[:-6] + "Z",
                            "modified": column1.modified.isoformat()[:-6] + "Z",
                        }
                    ],
                },
            ],
        )

    def test_retrieve_board(self):
        board = BoardFactory.create(name="scrum")
        column1 = BoardColumnFactory.create(board=board, name="wip")
        column2 = BoardColumnFactory.create(board=board, name="done")
        url = reverse("board-detail", args=[board.uuid])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "url": f"http://testserver{url}",
                "uuid": str(board.uuid),
                "name": "scrum",
                "slug": "scrum",
                "created": board.created.isoformat()[:-6] + "Z",
                "modified": board.modified.isoformat()[:-6] + "Z",
                "columns": [
                    {
                        "uuid": str(column1.uuid),
                        "name": "wip",
                        "slug": "wip",
                        "order": column1.order,
                        "created": column1.created.isoformat()[:-6] + "Z",
                        "modified": column1.modified.isoformat()[:-6] + "Z",
                    },
                    {
                        "uuid": str(column2.uuid),
                        "name": "done",
                        "slug": "done",
                        "order": column2.order,
                        "created": column2.created.isoformat()[:-6] + "Z",
                        "modified": column2.modified.isoformat()[:-6] + "Z",
                    },
                ],
            },
        )
