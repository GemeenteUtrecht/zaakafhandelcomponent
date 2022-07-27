from django.urls import reverse_lazy

import requests_mock
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import paginated_response

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
BRONORGANISATIE = "123456789"
IDENTIFICATIE = "ZAAK-0000001"


@requests_mock.Mocker()
@freeze_time("1999-12-31T23:59:59Z")
class ApiResponseTests(ESMixin, ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy(
        "zaak-checklist",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )

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
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            catalogus=cls.catalogus,
            omschrijving="ZT1",
            identificatie="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
        )
        cls.user = SuperUserFactory.create(is_staff=True)

    def test_retrieve_checklist(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaak["url"], json=self.zaak)
        m.get(self.zaaktype["url"], json=self.zaaktype)

        ChecklistFactory.create(zaak=self.zaak["url"])

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

    def test_retrieve_checklist_404(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 404)

    def test_create_checklist(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)

        ChecklistTypeFactory.create(
            zaaktype_identificatie=self.zaaktype["identificatie"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        data = {
            "answers": [],
        }

        # Assert current checklist count is 0
        self.assertEqual(Checklist.objects.count(), 0)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data=data)

        # Assert response code is 201 and checklist count is 1
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Checklist.objects.count(), 1)

    def test_create_checklist_fail_no_checklisttype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)

        ChecklistTypeFactory.create(
            zaaktype_identificatie="ZT2",
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        data = {
            "answers": [],
        }

        # Assert current checklist count is 0
        self.assertEqual(Checklist.objects.count(), 0)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"nonFieldErrors": ["Geen checklisttype gevonden foor ZAAKTYPE van ZAAK."]},
        )

    def test_create_checklist_fail_two_assignees_to_answer(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)

        checklisttype = ChecklistTypeFactory.create(
            zaaktype_identificatie=self.zaaktype["identificatie"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        ChecklistQuestionFactory.create(
            checklisttype=checklisttype, question="some-question"
        )
        group = GroupFactory.create()
        data = {
            "answers": [
                {
                    "question": "some-question",
                    "userAssignee": self.user.username,
                    "groupAssignee": group.name,
                    "answer": "some-answer",
                }
            ],
        }

        # Create checklist
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            [
                "An answer to a checklist question can not be assigned to both a user and a group."
            ],
        )

    def test_create_checklist_answer_not_found_in_mc(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)

        checklisttype = ChecklistTypeFactory.create(
            zaaktype_identificatie=self.zaaktype["identificatie"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        question = ChecklistQuestionFactory.create(
            checklisttype=checklisttype, question="some-question", order=1
        )
        QuestionChoiceFactory.create(
            question=question, name="Some answer", value="some-answer"
        )
        data = {
            "answers": [
                {"question": "some-question", "answer": "some-wrong-answer"},
            ],
        }

        # Create checklist
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            [
                "Antwoord `some-wrong-answer` werd niet teruggevonden in de opties: ['some-answer']."
            ],
        )

    def test_create_checklist_answer_answers_wrong_question(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)

        checklisttype = ChecklistTypeFactory.create(
            zaaktype_identificatie=self.zaaktype["identificatie"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        question = ChecklistQuestionFactory.create(
            checklisttype=checklisttype, question="some-question", order=1
        )
        QuestionChoiceFactory.create(
            question=question, name="Some answer", value="some-answer"
        )
        data = {
            "answers": [
                {
                    "question": "some-non-existent-question",
                    "answer": "some-wrong-answer",
                },
            ],
        }

        # Create checklist
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            [
                "Antwoord met vraag: `some-non-existent-question` beantwoordt niet een vraag van het gerelateerde checklisttype: Checklisttype voor ZAAKTYPE identificatie: ZT1 binnen CATALOGUS: https://open-zaak.nl/catalogi/api/v1//catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd."
            ],
        )

    def test_update_checklist(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaak["url"], json=self.zaak)
        m.get(self.zaaktype["url"], json=self.zaaktype)

        checklisttype = ChecklistTypeFactory.create(
            zaaktype_identificatie=self.zaaktype["identificatie"],
            zaaktype_catalogus=self.zaaktype["catalogus"],
        )
        question = ChecklistQuestionFactory.create(
            checklisttype=checklisttype, question="some-question", order=1
        )
        question_2 = ChecklistQuestionFactory.create(
            checklisttype=checklisttype, question="some-other-question", order=2
        )
        QuestionChoiceFactory.create(
            question=question, name="Some answer", value="some-answer"
        )
        checklist = ChecklistFactory.create(
            zaak=self.zaak["url"], checklisttype=checklisttype
        )
        answer = ChecklistAnswerFactory.create(
            checklist=checklist,
            question="some-other-question",
            answer="some-other-answer",
        )
        data = {
            "answers": [
                {"question": "some-question", "answer": "some-answer"},
                {
                    "question": answer.question,
                    "answer": "some-updated-answer",
                    "document": "https://some-document-url.com/",
                    "remarks": "some-remarks",
                    "groupAssignee": None,
                    "userAssignee": self.user.username,
                },
            ],
        }

        # assert one answer already exists
        self.assertEqual(ChecklistAnswer.objects.filter(checklist=checklist).count(), 1)
        self.assertEqual(
            ChecklistAnswer.objects.get(
                checklist=checklist, question="some-other-question"
            ).answer,
            "some-other-answer",
        )

        # Put checklist
        self.client.force_authenticate(self.user)
        response = self.client.put(self.endpoint, data=data)

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
            "created": "1999-12-31T23:59:59Z",
            "answers": [
                {
                    "answer": "some-answer",
                    "created": "1999-12-31T23:59:59Z",
                    "document": "",
                    "modified": "1999-12-31T23:59:59Z",
                    "question": "some-question",
                    "remarks": "",
                    "groupAssignee": None,
                    "userAssignee": None,
                },
                {
                    "answer": "some-updated-answer",
                    "created": "1999-12-31T23:59:59Z",
                    "document": "https://some-document-url.com/",
                    "modified": "1999-12-31T23:59:59Z",
                    "question": "some-other-question",
                    "remarks": "some-remarks",
                    "groupAssignee": None,
                    "userAssignee": self.user.username,
                },
            ],
        }
        data = response.json()
        self.assertEqual(expected_data["created"], data["created"])
        self.assertEqual(expected_data["answers"][1]["groupAssignee"], None)
        self.assertEqual(
            expected_data["answers"][1]["userAssignee"], self.user.username
        )
        self.assertTrue(expected_data["answers"][0] in data["answers"])
        self.assertTrue(expected_data["answers"][1] in data["answers"])
