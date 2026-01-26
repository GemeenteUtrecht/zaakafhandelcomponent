from django.urls import reverse

import requests_mock
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get

from ..models import Activity
from .factories import ActivityFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


@requests_mock.Mocker()
class ApiResponseTests(ClearCachesMixin, APITestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        ServiceFactory.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

        cls.catalogus = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        with freeze_time("1999-12-31 23:59:59"):
            cls.activity = ActivityFactory.create(zaak=cls.zaak["url"])

        cls.user = SuperUserFactory.create()

    def test_list_activity(self, m):
        self.client.force_authenticate(user=self.user)
        endpoint = reverse("activity-list")
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)

    def test_create_activity(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        self.client.force_authenticate(user=self.user)
        data = {
            "zaak": self.zaak["url"],
            "name": "some-activity",
        }

        endpoint = reverse("activity-list")

        # Assert current activity count is 1
        self.assertEqual(Activity.objects.count(), 1)

        # Mock zaak
        mock_resource_get(m, self.zaak)

        # Create activity
        response = self.client.post(endpoint, data=data)

        # Assert response code is 201 and activity count is 2
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Activity.objects.count(), 2)

    def test_delete_activity(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        self.client.force_authenticate(user=self.user)

        activity = ActivityFactory.create(zaak=self.zaak["url"])
        endpoint = reverse("activity-detail", kwargs={"pk": activity.pk})

        # Assert current activity count is 2
        self.assertEqual(Activity.objects.count(), 2)

        # Mock zaak
        mock_resource_get(m, self.zaak)

        # Delete activity
        response = self.client.delete(endpoint)

        # Assert response code is 200 and activity count is 1
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Activity.objects.count(), 1)

    def test_partial_update_assignee_activity(self, m):
        with freeze_time("1999-12-31 23:59:59"):
            mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
            self.client.force_authenticate(user=self.user)
            data = {
                "zaak": self.zaak["url"],
                "user_assignee": self.user.username,
            }
            endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})

            # Get old assignee value for assertion purposes
            old_assignee = self.activity.user_assignee

            # Mock zaak
            mock_resource_get(m, self.zaak)

            # Patch activity
            response = self.client.patch(endpoint, data=data)

            # Assert response code is 200
            self.assertEqual(response.status_code, 200)

            # Assert activity has been updated
            activity = Activity.objects.get(pk=self.activity.pk)
            self.assertTrue(old_assignee != activity.user_assignee)

            # Assert response data is as expected (different serializer than request)
            expected_data = {
                "id": self.activity.id,
                "url": f"http://testserver/api/activities/activities/{self.activity.id}",
                "zaak": self.zaak["url"],
                "name": self.activity.name,
                "remarks": "",
                "status": self.activity.status,
                "userAssignee": self.user.username,
                "groupAssignee": None,
                "document": self.activity.document,
                "created": "1999-12-31T23:59:59Z",
                "createdBy": None,
                "events": [],
            }
            data = response.json()
            self.assertEqual(expected_data, data)

    def test_partial_update_assignee_from_user_to_group_activity(self, m):
        with freeze_time("1999-12-31 23:59:59"):
            mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
            self.client.force_authenticate(user=self.user)
            group = GroupFactory.create()
            self.user.groups.add(group)
            data = {
                "zaak": self.zaak["url"],
                "group_assignee": group.name,
            }
            endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})

            # Mock zaak
            mock_resource_get(m, self.zaak)

            # Patch activity
            response = self.client.patch(endpoint, data=data)

            # Assert response code is 200
            self.assertEqual(response.status_code, 200)

            # Assert activity has been updated
            activity = Activity.objects.get(pk=self.activity.pk)
            self.assertEqual(activity.user_assignee, None)
            self.assertEqual(activity.group_assignee, group)

            # Assert response data is as expected (different serializer than request)
            expected_data = {
                "id": self.activity.id,
                "url": f"http://testserver/api/activities/activities/{self.activity.id}",
                "zaak": self.zaak["url"],
                "name": self.activity.name,
                "remarks": "",
                "status": self.activity.status,
                "userAssignee": None,
                "groupAssignee": group.name,
                "document": self.activity.document,
                "created": "1999-12-31T23:59:59Z",
                "createdBy": None,
                "events": [],
            }
            data = response.json()
            self.assertEqual(expected_data, data)

    def test_fail_partial_update_activity_invalid_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        self.client.force_authenticate(user=self.user)
        data = {
            "zaak": self.zaak["url"],
            "user_assignee": "some-invalid-user",
        }
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})

        # Mock zaak
        mock_resource_get(m, self.zaak)

        # Patch activity
        response = self.client.patch(endpoint, data=data)

        # Assert response code is 400
        self.assertEqual(response.status_code, 400)

    def test_fail_partial_update_activity_invalid_zaak_url(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        self.client.force_authenticate(user=self.user)
        data = {
            "zaak": self.zaak["url"] + "invalidate-this-url",
            "user_assignee": self.user.username,
        }
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})

        # Mock zaak
        m.get(self.zaak["url"] + "invalidate-this-url", json=self.zaak)
        mock_resource_get(m, self.zaak)

        # Patch activity
        response = self.client.patch(endpoint, data=data)

        # Assert response code is 400
        self.assertEqual(response.status_code, 400)

    def test_fail_not_allowed_to_put_activity(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        self.client.force_authenticate(user=self.user)
        data = {
            "zaak": self.zaak["url"] + "invalidate-this-url",
            "user_assignee": self.user.username,
        }
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})

        # Mock zaak
        mock_resource_get(m, self.zaak)

        # Put activity
        response = self.client.put(endpoint, data=data)

        # Assert response code is 405
        self.assertEqual(response.status_code, 405)
