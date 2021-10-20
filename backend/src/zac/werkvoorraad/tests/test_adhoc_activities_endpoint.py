from unittest.mock import patch

from django.urls import reverse

from freezegun import freeze_time
from furl import furl
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from zac.accounts.tests.factories import GroupFactory, UserFactory
from zac.activities.tests.factories import ActivityFactory
from zgw.models.zrc import Zaak

from ..api.data import ActivityGroup
from ..api.serializers import WorkStackAdhocActivitiesSerializer

ZAKEN_ROOT = "http://zaken.nl/api/v1/"


@freeze_time("2021-12-16T12:00:00Z")
class AdhocActivitiesTests(APITestCase):
    """
    Test the adhoc activities API endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            startdatum="2021-02-12",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
        )
        cls.zaak = factory(Zaak, zaak)
        cls.user = UserFactory.create()
        cls.activity = ActivityFactory.create(zaak=cls.zaak.url, user_assignee=cls.user)
        cls.group = GroupFactory.create()
        cls.user.groups.add(cls.group)
        cls.group_activity = ActivityFactory.create(
            zaak=cls.zaak.url, group_assignee=cls.group
        )
        cls.patch_get_zaak = patch(
            "zac.werkvoorraad.api.views.get_zaak", return_value=cls.zaak
        )

    def setUp(self):
        super().setUp()
        self.patch_get_zaak.start()
        self.addCleanup(self.patch_get_zaak.stop)

        self.client.force_authenticate(user=self.user)

    def test_other_user_logging_in(self):
        self.client.logout()
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        endpoint = reverse(
            "werkvoorraad:activities",
        )
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_workstack_adhoc_activities_serializer(self):
        activity_group = ActivityGroup(
            activities=[self.activity],
            zaak=self.zaak,
            zaak_url=self.zaak.url,
        )

        serializer = WorkStackAdhocActivitiesSerializer(activity_group)
        self.assertEqual(
            sorted(["activities", "zaak"]),
            sorted(list(serializer.data.keys())),
        )

    def test_adhoc_activities_endpoint(self):
        endpoint = reverse(
            "werkvoorraad:activities",
        )
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(sorted(["activities", "zaak"]), sorted(list(data[0].keys())))

    def test_adhoc_group_activities_no_group_specified(self):

        endpoint = reverse(
            "werkvoorraad:group-activities",
        )
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    def test_adhoc_group_activities_group_specified(self):
        endpoint = furl(
            reverse(
                "werkvoorraad:group-activities",
            )
        )
        endpoint.add({"group_assignee": self.group.name})
        response = self.client.get(endpoint.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data,
            [
                {
                    "activities": [{"name": self.group_activity.name}],
                    "zaak": {
                        "identificatie": self.zaak.identificatie,
                        "bronorganisatie": self.zaak.bronorganisatie,
                        "url": self.zaak.url,
                    },
                }
            ],
        )

    def test_adhoc_group_activities_group_specified_user_not_in_group(self):
        self.user.groups.remove(self.group)
        endpoint = furl(
            reverse(
                "werkvoorraad:group-activities",
            )
        )
        endpoint.add({"group_assignee": self.group.name})
        response = self.client.get(endpoint.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])
