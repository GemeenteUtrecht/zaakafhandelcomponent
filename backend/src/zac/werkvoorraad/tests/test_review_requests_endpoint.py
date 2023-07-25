from django.urls import reverse

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, UserFactory
from zac.contrib.kownsl.models import KownslConfig
from zac.contrib.kownsl.tests.utils import (
    ADVICE,
    CATALOGI_ROOT,
    KOWNSL_ROOT,
    REVIEW_REQUEST,
    ZAAK_URL,
    ZAKEN_ROOT,
)
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import paginated_response


@requests_mock.Mocker()
class ReviewRequestsTests(ESMixin, ClearCachesMixin, APITestCase):
    """
    Test the checklists questions API endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.service = Service.objects.create(
            label="Kownsl",
            api_type=APITypes.orc,
            api_root=KOWNSL_ROOT,
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            user_id="zac",
        )
        config = KownslConfig.get_solo()
        config.service = cls.service
        config.save()

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
            startdatum="2021-02-12",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
            zaaktype=cls.zaaktype["url"],
        )

        cls.endpoint = reverse(
            "werkvoorraad:review-requests",
        )

        cls.group = GroupFactory.create(name="some-group")
        # Let resolve_assignee get the right users and groups
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][0]["user_assignees"][0]
        )
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][1]["user_assignees"][0]
        )

    def test_workstack_review_requests_endpoint_no_zaak(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        self.refresh_index()

        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?pageSize=20&page=1&requester={self.user}",
            json=paginated_response([{**REVIEW_REQUEST, "reviews": [ADVICE]}]),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": REVIEW_REQUEST["id"],
                        "reviewType": REVIEW_REQUEST["reviewType"],
                        "openReviews": [
                            {
                                "deadline": "2022-04-15",
                                "users": [{"fullName": "some-other-author"}],
                                "groups": [],
                            }
                        ],
                        "isBeingReconfigured": REVIEW_REQUEST["isBeingReconfigured"],
                        "completed": REVIEW_REQUEST["numAdvices"]
                        + REVIEW_REQUEST["numApprovals"],
                        "zaak": None,
                        "advices": [
                            {
                                "created": ADVICE["created"],
                                "author": {
                                    "firstName": ADVICE["author"]["firstName"],
                                    "lastName": ADVICE["author"]["lastName"],
                                    "username": ADVICE["author"]["username"],
                                    "fullName": ADVICE["author"]["username"],
                                },
                                "advice": ADVICE["advice"],
                                "group": ADVICE["group"],
                            }
                        ],
                    }
                ],
            },
        )

    def test_workstack_review_requests_endpoint_found_zaak(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")

        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?pageSize=20&page=1&requester={self.user}",
            json=paginated_response([REVIEW_REQUEST]),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": REVIEW_REQUEST["id"],
                        "reviewType": REVIEW_REQUEST["reviewType"],
                        "openReviews": [
                            {
                                "deadline": "2022-04-15",
                                "users": [{"fullName": "some-other-author"}],
                                "groups": [],
                            }
                        ],
                        "isBeingReconfigured": REVIEW_REQUEST["isBeingReconfigured"],
                        "completed": REVIEW_REQUEST["numAdvices"]
                        + REVIEW_REQUEST["numApprovals"],
                        "zaak": {
                            "url": ZAAK_URL,
                            "identificatie": self.zaak["identificatie"],
                            "bronorganisatie": self.zaak["bronorganisatie"],
                            "status": {
                                "url": None,
                                "statustype": None,
                                "datumStatusGezet": None,
                                "statustoelichting": None,
                            },
                            "zaaktype": {
                                "url": self.zaaktype["url"],
                                "catalogus": self.zaaktype["catalogus"],
                                "omschrijving": self.zaaktype["omschrijving"],
                                "identificatie": self.zaaktype["identificatie"],
                            },
                            "omschrijving": self.zaak["omschrijving"],
                            "deadline": "2021-02-17T00:00:00Z",
                        },
                        "advices": [],
                    }
                ],
            },
        )