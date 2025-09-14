from copy import deepcopy
from unittest.mock import MagicMock, patch

from django.test import TestCase

import requests_mock
from django_camunda.utils import underscoreize
from freezegun import freeze_time
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import StatusType
from zgw_consumers.api_models.zaken import Status
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.models import User
from zac.accounts.tests.factories import UserFactory
from zac.contrib.objects.kownsl.camunda import ConfigureReviewRequestSerializer
from zac.contrib.objects.kownsl.constants import KownslTypes
from zac.contrib.objects.kownsl.tests.factories import (
    CATALOGI_ROOT,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
    advice_factory,
    review_object_factory,
    review_object_type_factory,
    review_request_factory,
    review_request_object_factory,
    review_request_object_type_factory,
    review_request_object_type_version_factory,
    reviews_factory,
)
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from ...services import (
    bulk_lock_review_requests_for_zaak,
    create_review_request,
    factory_review_request,
    factory_reviews,
    fetch_reviews,
    get_all_review_requests_for_zaak,
    get_review_request,
    lock_review_request,
    update_review_request,
)

REVIEW_REQUEST_OBJECTTYPE = review_request_object_type_factory()
REVIEW_OBJECTTYPE = review_object_type_factory()
REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION = review_request_object_type_version_factory()


@freeze_time("2020-01-01")
@requests_mock.Mocker()
class KownslAPITests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
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

        zaak_json = generate_oas_component("zrc", "schemas/Zaak", url=ZAAK_URL)
        cls.zaak = factory(Zaak, zaak_json)

        cls.review_request = review_request_factory()
        cls.advice = advice_factory()
        cls.reviews_advice = reviews_factory(reviews=[cls.advice])

        cls.review_object = review_object_factory(data=cls.reviews_advice)
        cls.review_request_object = review_request_object_factory()
        # Make sure all users associated to the REVIEW REQUEST exist
        users = deepcopy(
            [
                cls.review_request["assignedUsers"][0]["userAssignees"][0],
                cls.review_request["assignedUsers"][1]["userAssignees"][0],
                cls.review_request["requester"],
            ]
        )
        # del full_name
        for user in users:
            del user["fullName"]
            UserFactory.create(**underscoreize(user))

        cls.user = User.objects.get(
            username=cls.review_request["requester"]["username"]
        )

    def test_get_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([REVIEW_REQUEST_OBJECTTYPE]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([self.review_request_object]),
        )

        review_request = get_review_request(self.review_request["id"])
        self.assertEqual(str(review_request.id), self.review_request["id"])

    def test_get_reviews(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([REVIEW_OBJECTTYPE]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([self.review_object]),
        )

        reviews = fetch_reviews(review_request=self.review_request["id"])
        self.assertEqual(
            reviews[0]["record"]["data"], self.review_object["record"]["data"]
        )

    @patch("zac.core.api.validators.validate_zaak_documents")
    def test_create_review_request_object_and_relate_to_zaak(self, m, *mocks):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.post(
            f"{OBJECTS_ROOT}objects",
            json=self.review_request_object,
            status_code=201,
        )

        self.assertEqual(User.objects.count(), 2)
        data = {
            "assigned_users": [
                {
                    "deadline": "2022-04-14",
                    "user_assignees": ["some-author"],
                    "group_assignees": [],
                    "email_notification": False,
                },
                {
                    "deadline": "2022-04-15",
                    "user_assignees": [
                        "some-other-author",
                    ],
                    "group_assignees": [],
                    "email_notification": False,
                },
            ],
            "documents": ["http://some-documents.nl"],
            "toelichting": "some-toelichting",
            "zaakeigenschappen": [],
        }
        request = MagicMock()
        request.user = self.user
        task = MagicMock()
        task.form_key = "zac:configureAdviceRequest"
        context = {"request": request, "task": task}
        zaak_context = MagicMock()
        zaak_context.zaak = self.zaak
        with patch(
            "zac.contrib.objects.kownsl.camunda.get_zaak_context",
            return_value=zaak_context,
        ):

            serializer = ConfigureReviewRequestSerializer(data=data, context=context)
            serializer.is_valid(raise_exception=True)

        m.get(REVIEW_REQUEST_OBJECTTYPE["url"], json=REVIEW_REQUEST_OBJECTTYPE)
        m.get(
            REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION["url"],
            json=REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION,
        )
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([REVIEW_REQUEST_OBJECTTYPE]),
        )
        m.post(f"{ZAKEN_ROOT}zaakobjecten", json=[], status_code=201)
        with patch(
            "zac.contrib.objects.services._create_unique_uuid_for_object",
            return_value=self.review_request["id"],
        ):
            review_request = create_review_request(serializer.data)

        self.assertEqual(str(review_request.id), self.review_request["id"])
        self.assertEqual(review_request.zaak, ZAAK_URL)
        self.assertEqual(review_request.is_being_reconfigured, False)
        self.assertEqual(review_request.lock_reason, "")
        self.assertEqual(review_request.locked, False)
        self.assertEqual(
            review_request.metadata,
            {
                "process_instance_id": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
                "task_definition_id": "submitAdvice",
            },
        )
        self.assertEqual(review_request.num_reviews_given_before_change, 0)
        self.assertEqual(review_request.review_type, KownslTypes.advice)

    def test_get_all_review_requests_for_zaak(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([REVIEW_REQUEST_OBJECTTYPE]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([self.review_request_object]),
        )

        review_requests = get_all_review_requests_for_zaak(self.zaak)
        request = review_requests[0]
        self.assertEqual(str(request.id), self.review_request["id"])

    @patch("zac.core.api.validators.validate_zaak_documents")
    def test_update_assigned_users_review_request(self, m, *mocks):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([REVIEW_REQUEST_OBJECTTYPE]),
        )

        user = UserFactory(username="some-user")

        request = MagicMock()
        request.user = User.objects.get(
            username=self.review_request["requester"]["username"]
        )
        task = MagicMock()
        task.form_key = "zac:configureAdviceRequest"
        context = {"request": request, "task": task}
        zaak_context = MagicMock()
        zaak_context.zaak = self.zaak

        rr = factory_review_request(self.review_request)
        # Avoid patching fetch_reviews and everything
        reviews_advice = reviews_factory()
        rr.reviews = factory_reviews(reviews_advice).reviews
        rr.fetched_reviews = True

        with patch(
            "zac.contrib.objects.kownsl.camunda.get_zaak_context",
            return_value=zaak_context,
        ):
            with patch(
                "zac.contrib.objects.kownsl.camunda.get_review_request",
                return_value=rr,
            ):
                data = {
                    "id": self.review_request["id"],
                    "assigned_users": [
                        {
                            "user_assignees": ["some-user"],
                            "group_assignees": [],
                            "deadline": "2022-04-14",
                            "email_notification": True,
                        }
                    ],
                    "documents": ["http://some-documents.nl"],
                    "toelichting": "some-toelichting",
                    "zaakeigenschappen": [],
                }
                serializer = ConfigureReviewRequestSerializer(
                    data=data, context=context
                )
                serializer.is_valid(raise_exception=True)

        m.get(REVIEW_REQUEST_OBJECTTYPE["url"], json=REVIEW_REQUEST_OBJECTTYPE)
        m.get(
            REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION["url"],
            json=REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION,
        )

        m.patch(self.review_request_object["url"], json=self.review_request_object)

        with patch(
            "zac.contrib.objects.services.fetch_review_request",
            return_value=self.review_request_object,
        ):
            review_request = update_review_request(
                self.review_request["id"], requester=self.user, data=serializer.data
            )

        self.assertEqual(str(review_request.id), self.review_request["id"])
        self.assertEqual(
            m.last_request.json(),
            {
                "record": {
                    "index": 1,
                    "typeVersion": 4,
                    "data": {
                        "assignedUsers": [
                            {
                                "userAssignees": [
                                    {
                                        "email": user.email,
                                        "firstName": user.first_name,
                                        "fullName": user.get_full_name()
                                        or user.username,
                                        "lastName": user.last_name,
                                        "username": user.username,
                                    }
                                ],
                                "groupAssignees": [],
                                "emailNotification": True,
                                "deadline": "2022-04-14",
                            }
                        ],
                        "created": "2022-04-14 15:49:09.830235+00:00",
                        "documents": ["http://some-documents.nl"],
                        "id": "14aec7a0-06de-4b55-b839-a1c9a0415b46",
                        "isBeingReconfigured": False,
                        "locked": False,
                        "lockReason": "",
                        "metadata": {},
                        "numReviewsGivenBeforeChange": 1,
                        "requester": {
                            "email": self.user.email,
                            "firstName": self.user.first_name,
                            "fullName": self.user.get_full_name() or self.user.username,
                            "lastName": self.user.last_name,
                            "username": self.user.username,
                        },
                        "reviewType": "advice",
                        "toelichting": "some-toelichting",
                        "userDeadlines": {"user:some-user": "2022-04-14"},
                        "zaak": ZAAK_URL,
                        "zaakeigenschappen": [],
                    },
                    "geometry": "None",
                    "startAt": "1999-12-31",
                    "endAt": "None",
                    "registrationAt": "1999-12-31",
                    "correctionFor": 1,
                    "correctedBy": self.user.username,
                }
            },
        )

    def test_lock_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([REVIEW_REQUEST_OBJECTTYPE]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([self.review_request_object]),
        )
        rr = review_request_object_factory(
            record__data__locked=True, record__data__lockReason="some-reason"
        )
        rr["record"]["data"]["locked"] = True
        rr["record"]["data"]["lockReason"] = "some-reason"

        m.patch(rr["url"], json=rr)

        review_request = lock_review_request(
            self.review_request["id"], lock_reason="some-reason"
        )
        self.assertEqual(str(review_request.id), self.review_request["id"])
        self.assertTrue(m.last_request.json()["record"]["data"]["locked"])

    def test_bulk_lock_review_request_for_zaak(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        rr1 = review_request_factory()
        rr1["locked"] = True
        rr2 = review_request_factory()
        rr2["locked"] = False
        review_requests = [
            factory_review_request(rr1),
            factory_review_request(rr2),
        ]

        status = generate_oas_component(
            "zrc",
            "schemas/Status",
            url=f"{ZAKEN_ROOT}statussen/dd4573d0-4d99-4e90-a05c-e08911e8673e",
            statustype=f"{CATALOGI_ROOT}statustypen/c612f300-8e16-4811-84f4-78c99fdebe74",
            statustoelichting="some-statustoelichting",
        )
        status = factory(Status, status)
        statustype = generate_oas_component(
            "ztc",
            "schemas/StatusType",
            url=f"{CATALOGI_ROOT}statustypen/c612f300-8e16-4811-84f4-78c99fdebe74",
            is_eindstatus=True,
        )
        status.statustype = factory(StatusType, statustype)
        zaak = deepcopy(self.zaak)
        zaak.status = status

        with patch(
            "zac.contrib.objects.services.parallel", return_value=mock_parallel()
        ):
            with patch(
                "zac.contrib.objects.services.get_all_review_requests_for_zaak",
                return_value=review_requests,
            ):
                with patch(
                    "zac.contrib.objects.services.lock_review_request"
                ) as mock_lock_review_request:
                    bulk_lock_review_requests_for_zaak(zaak)

        mock_lock_review_request.assert_called_once()
