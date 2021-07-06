from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.tests.factories import UserFactory
from zac.core.models import CoreConfig
from zac.core.tests.utils import ClearCachesMixin

OBJECTTYPES_ROOT = "http://objecttype.nl/api/v1/"


@requests_mock.Mocker()
class ObjecttypesListTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.objecttypes_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )

        cls.objecttype_1 = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/1",
            "name": "tree",
            "namePlural": "trees",
            "description": "",
            "data_classification": "",
            "maintainer_organization": "",
            "maintainer_department": "",
            "contact_person": "",
            "contact_email": "",
            "source": "",
            "update_frequency": "",
            "provider_organization": "",
            "documentation_url": "",
            "labels": {},
            "created_at": "2019-08-24",
            "modified_at": "2019-08-24",
            "versions": [],
        }
        cls.objecttype_2 = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/2",
            "name": "bin",
            "namePlural": "bins",
            "description": "",
            "data_classification": "",
            "maintainer_organization": "",
            "maintainer_department": "",
            "contact_person": "",
            "contact_email": "",
            "source": "",
            "update_frequency": "",
            "provider_organization": "",
            "documentation_url": "",
            "labels": {},
            "created_at": "2019-08-24",
            "modified_at": "2019-08-24",
            "versions": [],
        }

    def test_not_authenticated(self, m):
        list_url = reverse("objecttypes-list")
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_objecttypes(self, m):
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=[self.objecttype_1, self.objecttype_2],
        )

        config = CoreConfig.get_solo()
        config.primary_objecttypes_api = self.objecttypes_service
        config.save()

        list_url = reverse("objecttypes-list")
        user = UserFactory.create()

        self.client.force_authenticate(user=user)
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(2, len(response.json()))
