from django.urls import reverse

import requests_mock
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory
from zac.core.tests.utils import ClearCachesMixin

from ..models import Checklist, ChecklistAnswer
from .factories import (
    ChecklistAnswerFactory,
    ChecklistFactory,
    ChecklistQuestionFactory,
    ChecklistTypeFactory,
    QuestionChoiceFactory,
)

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


@requests_mock.Mocker()
@freeze_time("1999-12-31T23:59:59Z")
class ApiResponseTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        Service.objects.create(
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
        cls.user = SuperUserFactory.create(is_staff=True)

    def test_list_checklists(self, m):
        ChecklistFactory.create(zaak="https://some-zaak-url.com")
        self.client.force_authenticate(user=self.user)
        endpoint = reverse("checklist-list")
        response = self.client.get(endpoint, {"zaak": "https://some-zaak-url.com"})
        self.assertEqual(response.status_code, 200)

    def test_create_checklist(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        self.client.force_authenticate(user=self.user)
        clt = ChecklistTypeFactory.create(
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
        data = {"zaak": zaak["url"], "checklistType": clt.pk, "answers": []}

        endpoint = reverse("checklist-list")

        # Assert current checklist count is 0
        self.assertEqual(Checklist.objects.count(), 0)

        # Mock zaak
        m.get(zaak["url"], json=zaak)

        # Mock zaaktype
        m.get(self.zaaktype["url"], json=self.zaaktype)

        # Create checklist
        response = self.client.post(endpoint, data=data)

        # Assert response code is 201 and checklist count is 1
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Checklist.objects.count(), 1)

    def test_create_checklist_fail_different_checklist_type(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        self.client.force_authenticate(user=self.user)
        clt = ChecklistTypeFactory.create(
            zaaktype=self.zaaktype["url"],
            zaaktype_omschrijving=self.zaaktype["omschrijving"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        clt2 = ChecklistTypeFactory.create(
            zaaktype_omschrijving="some-other-omschrijving",
            zaaktype_catalogus="https://some-other-catalogus-url.com/",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=self.zaaktype["url"],
        )
        data = {"zaak": zaak["url"], "checklistType": clt2.pk, "answers": []}

        endpoint = reverse("checklist-list")

        # Mock zaak
        m.get(zaak["url"], json=zaak)

        # Mock zaaktype
        m.get(self.zaaktype["url"], json=self.zaaktype)

        # Create checklist
        response = self.client.post(endpoint, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "nonFieldErrors": [
                    "ZAAKTYPE of checklist_type is not related to the ZAAKTYPE of the ZAAK."
                ]
            },
        )

    def test_create_checklist_fail_two_assignees(self, m):
        self.client.force_authenticate(user=self.user)
        group = GroupFactory.create()
        checklist_type = ChecklistTypeFactory.create()
        data = {
            "zaak": "https://some-zaak-url.com/",
            "checklistType": checklist_type.pk,
            "userAssignee": self.user.username,
            "groupAssignee": group.name,
            "answers": [],
        }

        endpoint = reverse("checklist-list")

        # Create checklist
        response = self.client.post(endpoint, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "nonFieldErrors": [
                    "A checklist can not be assigned to both a user and a group."
                ]
            },
        )

    def test_create_checklist_answer_not_found_in_mc(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        self.client.force_authenticate(user=self.user)
        checklist_type = ChecklistTypeFactory.create(
            zaaktype=self.zaaktype["url"],
            zaaktype_omschrijving=self.zaaktype["omschrijving"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        question = ChecklistQuestionFactory.create(
            checklist_type=checklist_type, question="some-question", order=1
        )
        QuestionChoiceFactory.create(
            question=question, name="Some answer", value="some-answer"
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=self.zaaktype["url"],
        )
        data = {
            "zaak": zaak["url"],
            "checklist_type": checklist_type.uuid,
            "answers": [
                {"question": "some-question", "answer": "some-wrong-answer"},
            ],
        }
        endpoint = reverse("checklist-list")

        # Mock zaak
        m.get(zaak["url"], json=zaak)

        # Mock zaaktype
        m.get(self.zaaktype["url"], json=self.zaaktype)

        # Create checklist
        response = self.client.post(endpoint, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            [
                "Answer `some-wrong-answer` was not found in the options: ['some-answer']."
            ],
        )

    def test_create_checklist_answer_answers_wrong_question(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        self.client.force_authenticate(user=self.user)
        checklist_type = ChecklistTypeFactory.create(
            zaaktype=self.zaaktype["url"],
            zaaktype_omschrijving=self.zaaktype["omschrijving"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        question = ChecklistQuestionFactory.create(
            checklist_type=checklist_type, question="some-question", order=1
        )
        QuestionChoiceFactory.create(
            question=question, name="Some answer", value="some-answer"
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=self.zaaktype["url"],
        )
        data = {
            "zaak": zaak["url"],
            "checklist_type": checklist_type.uuid,
            "answers": [
                {
                    "question": "some-non-existent-question",
                    "answer": "some-wrong-answer",
                },
            ],
        }
        endpoint = reverse("checklist-list")

        # Mock zaak
        m.get(zaak["url"], json=zaak)

        # Mock zaaktype
        m.get(self.zaaktype["url"], json=self.zaaktype)

        # Create checklist
        response = self.client.post(endpoint, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            [
                "Answer with question: `some-non-existent-question` didn't answer a question of the related checklist_type: Checklist type of `ZT1` within `https://open-zaak.nl/catalogi/api/v1//catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd`."
            ],
        )

    def test_update_checklist(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        self.client.force_authenticate(user=self.user)
        checklist_type = ChecklistTypeFactory.create(
            zaaktype=self.zaaktype["url"],
            zaaktype_omschrijving=self.zaaktype["omschrijving"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        question = ChecklistQuestionFactory.create(
            checklist_type=checklist_type, question="some-question", order=1
        )
        question_2 = ChecklistQuestionFactory.create(
            checklist_type=checklist_type, question="some-other-question", order=2
        )
        QuestionChoiceFactory.create(
            question=question, name="Some answer", value="some-answer"
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=self.zaaktype["url"],
        )
        checklist = ChecklistFactory.create(
            zaak=zaak["url"], checklist_type=checklist_type
        )
        answer = ChecklistAnswerFactory.create(
            checklist=checklist,
            question="some-other-question",
            answer="some-other-answer",
        )
        data = {
            "zaak": zaak["url"],
            "checklist_type": checklist_type.uuid,
            "userAssignee": self.user.username,
            "answers": [
                {"question": "some-question", "answer": "some-answer"},
                {
                    "question": answer.question,
                    "answer": "some-updated-answer",
                },
            ],
        }
        endpoint = reverse("checklist-detail", kwargs={"pk": checklist.pk})

        # Mock zaak
        m.get(zaak["url"], json=zaak)

        # Mock zaaktype
        m.get(self.zaaktype["url"], json=self.zaaktype)

        # assert one answer already exists
        self.assertEqual(ChecklistAnswer.objects.filter(checklist=checklist).count(), 1)
        self.assertEqual(
            ChecklistAnswer.objects.get(
                checklist=checklist, question="some-other-question"
            ).answer,
            "some-other-answer",
        )

        # Put checklist
        response = self.client.put(endpoint, data=data)

        # Assert response code is 200
        self.assertEqual(response.status_code, 200)

        # Assert answer: only 1 exists and has value of answer
        self.assertTrue(
            ChecklistAnswer.objects.filter(checklist=checklist).exists(),
        )
        self.assertEqual(
            ChecklistAnswer.objects.filter(checklist=checklist).count(),
            2,
        )
        self.assertEqual(
            ChecklistAnswer.objects.get(
                checklist=checklist, question="some-question"
            ).answer,
            "some-answer",
        )
        self.assertEqual(
            ChecklistAnswer.objects.get(
                checklist=checklist, question="some-other-question"
            ).answer,
            "some-updated-answer",
        )

        # Assert response data is as expected
        expected_data = {
            "url": f"http://testserver/api/checklists/checklists/{checklist.pk}",
            "created": "1999-12-31T23:59:59Z",
            "checklistType": str(checklist_type.uuid),
            "groupAssignee": None,
            "userAssignee": self.user.username,
            "zaak": "https://open-zaak.nl/zaken/api/v1/zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            "answers": [
                {
                    "question": "some-other-question",
                    "answer": "some-updated-answer",
                    "created": "1999-12-31T23:59:59Z",
                    "modified": "1999-12-31T23:59:59Z",
                },
                {
                    "question": "some-question",
                    "answer": "some-answer",
                    "created": "1999-12-31T23:59:59Z",
                    "modified": "1999-12-31T23:59:59Z",
                },
            ],
        }

        data = response.json()
        self.assertEqual(expected_data, data)
