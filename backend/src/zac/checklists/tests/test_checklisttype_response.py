from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import requests_mock
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import SuperUserFactory
from zac.core.tests.utils import ClearCachesMixin

from ..models import ChecklistQuestion, ChecklistType, QuestionChoice
from .factories import ChecklistQuestionFactory, ChecklistTypeFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


@requests_mock.Mocker()
@freeze_time("1999-12-31T23:59:59Z")
class ApiResponseTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
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
        cls.user = SuperUserFactory.create(is_staff=True)

    def test_list_checklisttypes(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        ChecklistTypeFactory.create(
            zaaktype=self.zaaktype["url"],
            zaaktype_omschrijving=self.zaaktype["omschrijving"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=self.zaaktype["url"],
        )
        self.client.force_authenticate(user=self.user)
        m.get(zaak["url"], json=zaak)
        m.get(self.zaaktype["url"], json=self.zaaktype)
        endpoint = reverse("checklisttype-list")
        response = self.client.get(endpoint, {"zaak": zaak["url"]})
        self.assertEqual(response.status_code, 200)

    def test_create_checklisttype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)

        data = {
            "zaaktype": self.zaaktype["url"],
            "questions": [
                {
                    "question": "some-question",
                    "choices": [{"name": "Some Value", "value": "some-value"}],
                    "order": 1,
                }
            ],
        }

        endpoint = reverse("checklisttype-list")
        self.client.force_authenticate(user=self.user)
        self.assertFalse(ChecklistQuestion.objects.exists())
        self.assertFalse(QuestionChoice.objects.exists())
        self.assertFalse(ChecklistType.objects.exists())
        response = self.client.post(endpoint, data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ChecklistQuestion.objects.exists())
        self.assertTrue(QuestionChoice.objects.exists())
        self.assertTrue(ChecklistType.objects.exists())

    def test_create_checklisttype_already_exists(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)
        ChecklistTypeFactory.create(
            zaaktype=self.zaaktype["url"],
            zaaktype_omschrijving=self.zaaktype["omschrijving"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        data = {"zaaktype": self.zaaktype["url"], "questions": []}

        endpoint = reverse("checklisttype-list")
        self.client.force_authenticate(user=self.user)
        response = self.client.post(endpoint, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            [
                "Checklist type met deze CATALOGUS of ZAAKTYPE en Omschrijving bestaat al."
            ],
        )

    def test_create_checklisttype_question_order_error(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)

        data = {
            "zaaktype": self.zaaktype["url"],
            "questions": [
                {
                    "question": "some-question",
                    "choices": [{"name": "Some Value", "value": "some-value"}],
                    "order": 1,
                },
                {
                    "question": "some-other-question",
                    "choices": [],
                    "order": 1,
                },
            ],
        }

        endpoint = reverse("checklisttype-list")
        self.client.force_authenticate(user=self.user)
        response = self.client.post(endpoint, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "nonFieldErrors": [
                    _(
                        "The order of the questions has to be unique. Question `some-other-question` and question `some-question` both have order `1`."
                    )
                ]
            },
        )

    def test_create_checklisttype_question_order_normalization(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)

        data = {
            "zaaktype": self.zaaktype["url"],
            "questions": [
                {
                    "question": "some-question",
                    "choices": [{"name": "Some Value", "value": "some-value"}],
                    "order": 10,
                },
                {
                    "question": "some-other-question",
                    "choices": [],
                    "order": 3,
                },
            ],
        }

        endpoint = reverse("checklisttype-list")
        self.client.force_authenticate(user=self.user)
        response = self.client.post(endpoint, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["questions"],
            [
                {
                    "question": "some-question",
                    "order": 2,
                    "choices": [{"name": "Some Value", "value": "some-value"}],
                    "isMultipleChoice": True,
                },
                {
                    "question": "some-other-question",
                    "order": 1,
                    "choices": [],
                    "isMultipleChoice": False,
                },
            ],
        )

    def test_update_checklisttype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        checklist_type = ChecklistTypeFactory.create(
            zaaktype=self.zaaktype["url"],
            zaaktype_omschrijving=self.zaaktype["omschrijving"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        ChecklistQuestionFactory.create(
            checklist_type=checklist_type, question="some-question", order=1
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=self.zaaktype["url"],
        )
        self.client.force_authenticate(user=self.user)
        m.get(self.zaaktype["url"], json=self.zaaktype)
        data = {
            "zaaktype": self.zaaktype["url"],
            "questions": [
                {
                    "question": "some-question",
                    "choices": [{"name": "Some Value", "value": "some-value"}],
                    "order": 10,
                },
                {
                    "question": "some-other-question",
                    "choices": [],
                    "order": 3,
                },
            ],
        }
        endpoint = reverse("checklisttype-detail", kwargs={"pk": checklist_type.pk})
        response = self.client.put(endpoint, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChecklistType.objects.count(), 1)
        self.assertEqual(ChecklistQuestion.objects.count(), 2)
        self.assertEqual(QuestionChoice.objects.count(), 1)
