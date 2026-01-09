from copy import deepcopy
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import UserFactory
from zac.contrib.objects.kownsl.tests.factories import (
    CATALOGI_ROOT,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
    advice_factory,
    review_object_factory,
    review_object_type_version_factory,
    review_request_factory,
    review_request_object_factory,
    review_request_object_type_version_factory,
    reviews_factory,
)
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
REVIEW_OBJECTTYPE = review_object_type_version_factory()
REVIEW_REQUEST_OBJECTTYPE = review_request_object_type_version_factory()


@requests_mock.Mocker()
class ReviewRequestsTests(ClearCachesMixin, ESMixin, APITestCase):
    """
    Test the checklists questions API endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        cls.maxDiff = None
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
        cls.review_request = review_request_factory()

    @patch("zac.core.services.fetch_objecttypes", return_value=[])
    def test_workstack_review_requests_endpoint_no_zaak(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        mock_resource_get(m, self.catalogus)

        rr_object = review_request_object_factory(record__data=self.review_request)

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=20&page=1",
            json=paginated_response([rr_object]),
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
                        "id": self.review_request["id"],
                        "reviewType": self.review_request["reviewType"],
                        "openReviews": [
                            {
                                "deadline": "2022-04-14",
                                "groups": [],
                                "users": [
                                    self.review_request["assignedUsers"][0][
                                        "userAssignees"
                                    ][0]["fullName"]
                                ],
                            },
                            {
                                "deadline": "2022-04-15",
                                "groups": [],
                                "users": [
                                    self.review_request["assignedUsers"][1][
                                        "userAssignees"
                                    ][0]["fullName"]
                                ],
                            },
                        ],
                        "isBeingReconfigured": self.review_request[
                            "isBeingReconfigured"
                        ],
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

        rr_object = review_request_object_factory(record__data=self.review_request)

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=20&page=1",
            json=paginated_response([rr_object]),
        )

        self.client.force_authenticate(user=self.user)

        advice = advice_factory()
        reviews_advice = reviews_factory(reviews=[advice])

        review_object = review_object_factory(record__data=reviews_advice)

        with patch(
            "zac.contrib.objects.services.fetch_reviews",
            return_value=[review_object],
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
                        "id": self.review_request["id"],
                        "reviewType": self.review_request["reviewType"],
                        "openReviews": [
                            {
                                "deadline": "2022-04-15",
                                "groups": [],
                                "users": [
                                    self.review_request["assignedUsers"][1][
                                        "userAssignees"
                                    ][0]["fullName"]
                                ],
                            }
                        ],
                        "isBeingReconfigured": self.review_request[
                            "isBeingReconfigured"
                        ],
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
                                    "email": advice["author"]["email"],
                                    "firstName": advice["author"]["firstName"],
                                    "lastName": advice["author"]["lastName"],
                                    "username": advice["author"]["username"],
                                    "fullName": advice["author"]["fullName"],
                                },
                                "advice": advice["advice"],
                                "group": dict(),
                                "created": advice["created"],
                            }
                        ],
                    }
                ],
            },
            response.json(),
        )
