from unittest.mock import MagicMock, patch

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
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.objects.checklists.tests.utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CHECKLIST_OBJECT,
    IDENTIFICATIE,
    ZAAK_URL,
    ZAKEN_ROOT,
)


@freeze_time("2021-12-16T12:00:00Z")
class ChecklistAnswersTests(ESMixin, ClearCachesMixin, APITestCase):
    """
    Test the checklists questions API endpoint.
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
            url=ZAAK_URL,
            identificatie=IDENTIFICATIE,
            bronorganisatie=BRONORGANISATIE,
            startdatum="2021-02-12",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
            zaaktype=cls.zaaktype["url"],
        )

        cls.endpoint = reverse(
            "werkvoorraad:checklists",
        )

    def test_workstack_checklist_answers_endpoint(self):
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

        user_checklist = {**CHECKLIST_OBJECT["record"]["data"]}
        user_checklist["answers"][0]["user_assignee"] = self.user.username
        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.werkvoorraad.views.fetch_all_checklists_for_user",
            return_value=[user_checklist],
        ):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "checklistQuestions": [
                        {
                            "question": user_checklist["answers"][0]["question"],
                        },
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

    def test_workstack_checklist_answers_endpoint_no_zaak(self):
        self.refresh_index()

        self.client.force_authenticate(user=self.user)
        user_checklist = {**CHECKLIST_OBJECT["record"]["data"]}
        user_checklist["answers"][0]["user_assignee"] = self.user.username
        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.werkvoorraad.views.fetch_all_checklists_for_user",
            return_value=[user_checklist],
        ):
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

        user_checklist = {**CHECKLIST_OBJECT["record"]["data"]}
        user_checklist["answers"][0]["user_assignee"] = self.user.username
        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.werkvoorraad.views.fetch_all_checklists_for_user",
            return_value=[],
        ):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_workstack_group_checklist_answers_group_specified(self):
        self.user.groups.add(self.group_1)
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

        group_checklist = {**CHECKLIST_OBJECT["record"]["data"]}
        group_checklist["answers"][0]["group_assignee"] = self.group_1.name
        self.client.force_authenticate(user=self.user)
        endpoint = reverse("werkvoorraad:group-checklists")
        with patch(
            "zac.werkvoorraad.views.fetch_all_checklists_for_user_groups",
            return_value=[group_checklist],
        ):
            response = self.client.get(endpoint)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "checklistQuestions": [
                        {
                            "question": group_checklist["answers"][0]["question"],
                        },
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
