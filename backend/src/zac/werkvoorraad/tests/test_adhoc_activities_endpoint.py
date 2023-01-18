from unittest.mock import MagicMock

from django.urls import reverse

from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    GroupFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.activities.tests.factories import ActivityFactory, EventFactory
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin

from ..data import ActivityGroup
from ..serializers import WorkStackAdhocActivitiesSerializer

ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "http://catalogus.nl/api/v1/"


@freeze_time("2021-12-16T12:00:00Z")
class AdhocActivitiesTests(ESMixin, ClearCachesMixin, APITestCase):
    """
    Test the adhoc activities API endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.user = UserFactory.create()
        cls.group_1 = GroupFactory.create()
        cls.group_2 = GroupFactory.create()
        cls.catalogus = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            omschrijving="ZT1",
            catalogus=cls.catalogus,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            startdatum="2021-02-12",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
            zaaktype=cls.zaaktype["url"],
        )

        cls.endpoint = reverse(
            "werkvoorraad:activities",
        )

        user_activity = ActivityFactory.create(
            zaak=cls.zaak["url"], user_assignee=cls.user
        )
        cls.user_activity_group = ActivityGroup(
            activities=[user_activity],
            zaak=cls.zaak,
            zaak_url=cls.zaak["url"],
        )
        EventFactory.create(activity=user_activity)

        group_activity = ActivityFactory.create(
            zaak=cls.zaak["url"], group_assignee=cls.group_1
        )
        cls.group_activity_group = ActivityGroup(
            activities=[group_activity],
            zaak=cls.zaak,
            zaak_url=cls.zaak["url"],
        )
        EventFactory.create(activity=group_activity)

    def test_workstack_adhoc_activities_serializer(self):
        request = MagicMock()
        request.user.return_value = self.user
        serializer = WorkStackAdhocActivitiesSerializer(
            self.user_activity_group, context={"request": request}
        )
        self.assertEqual(
            serializer.data,
            {
                "activities": [
                    {
                        "name": self.user_activity_group.activities[0].name,
                        "user_assignee": self.user.username,
                        "group_assignee": None,
                    }
                ],
                "zaak": {
                    "url": self.zaak["url"],
                    "identificatie": self.zaak["identificatie"],
                    "bronorganisatie": self.zaak["bronorganisatie"],
                    "status": None,
                },
            },
        )

    def test_workstack_adhoc_activities_endpoint(self):
        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "activities": [
                        {
                            "name": self.user_activity_group.activities[0].name,
                            "groupAssignee": None,
                            "userAssignee": self.user.username,
                        }
                    ],
                    "zaak": {
                        "url": self.zaak["url"],
                        "identificatie": self.zaak["identificatie"],
                        "bronorganisatie": self.zaak["bronorganisatie"],
                        "status": {
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                            "statustype": None,
                            "url": None,
                        },
                    },
                }
            ],
        )

    def test_workstack_adhoc_activities_endpoint_no_zaak(self):
        self.refresh_index()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data, [])

    def test_other_user_logging_in(self):
        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()
        self.client.logout()
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_workstack_adhoc_group_activities_no_group_specified_in_url(self):
        endpoint = reverse("werkvoorraad:group-activities")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    def test_workstack_adhoc_group_activities_user_not_part_of_group(self):
        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        endpoint = reverse("werkvoorraad:group-activities")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    def test_workstack_adhoc_group_activities_group_specified(self):
        self.user.groups.add(self.group_1)
        self.user.groups.add(self.group_2)
        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        endpoint = reverse("werkvoorraad:group-activities")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data,
            [
                {
                    "activities": [
                        {
                            "name": self.group_activity_group.activities[0].name,
                            "userAssignee": None,
                            "groupAssignee": self.group_1.name,
                        }
                    ],
                    "zaak": {
                        "url": self.zaak["url"],
                        "identificatie": self.zaak["identificatie"],
                        "bronorganisatie": self.zaak["bronorganisatie"],
                        "status": {
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                            "statustype": None,
                            "url": None,
                        },
                    },
                }
            ],
        )
        self.user.groups.remove(self.group_1)
        self.user.groups.remove(self.group_2)

    def test_workstack_adhoc_group_activities_part_of_different_group(self):
        self.user.groups.add(self.group_2)
        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        endpoint = reverse("werkvoorraad:group-activities")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])
        self.user.groups.remove(self.group_2)
