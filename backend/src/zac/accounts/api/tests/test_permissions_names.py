from dataclasses import dataclass
from unittest.mock import patch

from django.urls import reverse_lazy

from rest_framework import status
from rest_framework.test import APITestCase

from ...tests.factories import SuperUserFactory

# create a test permission in the separate registry
test_registry = {}


@dataclass(frozen=True)
class TestPermission:
    name: str
    description: str

    def __post_init__(self):
        test_registry[self.name] = self


permission1 = TestPermission(name="permission 1", description="some description 1")
permission2 = TestPermission(name="permission 2", description="some description 2")


class PermissionsAPITests(APITestCase):
    url = reverse_lazy("permissions")

    def setUp(self) -> None:
        super().setUp()

        self.user = SuperUserFactory.create()
        self.client.force_authenticate(self.user)

        patcher_registry = patch("zac.accounts.api.views.registry", new=test_registry)
        self.mocked_registry = patcher_registry.start()
        self.addCleanup(patcher_registry.stop)

    def test_get_available_permissions(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {"name": "permission 1", "description": "some description 1"},
                {"name": "permission 2", "description": "some description 2"},
            ],
        )
