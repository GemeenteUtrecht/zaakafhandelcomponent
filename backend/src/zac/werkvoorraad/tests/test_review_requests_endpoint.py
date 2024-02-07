from unittest.mock import patch

from django.urls import reverse

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, UserFactory
from zac.contrib.objects.kownsl.tests.utils import (
    ADVICE,
    CATALOGI_ROOT,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    REVIEW_OBJECT,
    REVIEW_OBJECTTYPE,
    REVIEW_REQUEST,
    REVIEW_REQUEST_OBJECT,
    REVIEW_REQUEST_OBJECTTYPE,
    ZAAK_URL,
    ZAKEN_ROOT,
)
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response

CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


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
        objects_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        objecttypes_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        config = CoreConfig.get_solo()
        config.primary_objects_api = objects_service
        config.primary_objecttypes_api = objecttypes_service
        config.save()

        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.review_request_objecttype = REVIEW_REQUEST_OBJECTTYPE["url"]
        meta_config.review_objecttype = REVIEW_OBJECTTYPE["url"]
        meta_config.save()

        cls.user = UserFactory.create()
        cls.group_1 = GroupFactory.create()
        cls.group_2 = GroupFactory.create()
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            omschrijving="ZT1",
            catalogus=cls.catalogus["url"],
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
            username=REVIEW_REQUEST["assignedUsers"][0]["userAssignees"][0]
        )
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][1]["userAssignees"][0]
        )

    @patch("zac.core.services.fetch_objecttypes", return_value=[])
    def test_workstack_review_requests_endpoint_no_zaak(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        mock_resource_get(m, self.catalogus)
        self.refresh_index()

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=20&page=1",
            json=paginated_response([REVIEW_REQUEST_OBJECT]),
        )

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.services.fetch_reviews",
            return_value=[],
        ):
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
                                "deadline": "2022-04-14",
                                "groups": [],
                                "users": ["Some First Some Last"],
                            },
                            {
                                "deadline": "2022-04-15",
                                "groups": [],
                                "users": ["Some Other First Some Last"],
                            },
                        ],
                        "isBeingReconfigured": REVIEW_REQUEST["isBeingReconfigured"],
                        "completed": 0,
                        "zaak": None,
                        "advices": [],
                    }
                ],
            },
        )

    @patch("zac.core.services.fetch_objecttypes", return_value=[])
    def test_workstack_review_requests_endpoint_found_zaak(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        mock_resource_get(m, self.catalogus)
        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=20&page=1",
            json=paginated_response([REVIEW_REQUEST_OBJECT]),
        )

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.services.fetch_reviews",
            return_value=[REVIEW_OBJECT],
        ):
            response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
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
                                "groups": [],
                                "users": ["Some Other First Some Last"],
                            }
                        ],
                        "isBeingReconfigured": REVIEW_REQUEST["isBeingReconfigured"],
                        "completed": 1,
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
                                "catalogusDomein": self.catalogus["domein"],
                                "omschrijving": self.zaaktype["omschrijving"],
                                "identificatie": self.zaaktype["identificatie"],
                            },
                            "omschrijving": self.zaak["omschrijving"],
                            "deadline": "2021-02-17T00:00:00Z",
                        },
                        "advices": [
                            {
                                "author": {
                                    "firstName": ADVICE["author"]["firstName"],
                                    "lastName": ADVICE["author"]["lastName"],
                                    "username": ADVICE["author"]["username"],
                                    "fullName": ADVICE["author"]["fullName"],
                                },
                                "advice": ADVICE["advice"],
                                "group": dict(),
                                "created": ADVICE["created"],
                            }
                        ],
                    }
                ],
            },
            response.json(),
        )
