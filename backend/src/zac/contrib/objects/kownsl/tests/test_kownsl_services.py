from copy import deepcopy
from unittest.mock import MagicMock, patch

from django.test import TestCase

import requests_mock
from django_camunda.utils import underscoreize
from freezegun import freeze_time
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.models import User
from zac.accounts.tests.factories import UserFactory
from zac.contrib.objects.kownsl.camunda import ConfigureReviewRequestSerializer
from zac.contrib.objects.kownsl.constants import KownslTypes
from zac.contrib.objects.kownsl.tests.utils import (
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    REVIEW_OBJECT,
    REVIEW_OBJECTTYPE,
    REVIEW_REQUEST_OBJECT,
    REVIEW_REQUEST_OBJECTTYPE,
    REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION,
    ZAAK_URL,
    ZAKEN_ROOT,
    AdviceFactory,
    AssignedUsersFactory,
    ReviewRequestFactory,
    ReviewsAdviceFactory,
    UserAssigneeFactory,
)
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

from ...services import (
    create_review_request,
    factory_review_request,
    factory_reviews,
    fetch_reviews,
    get_all_review_requests_for_zaak,
    get_review_request,
    lock_review_request,
    update_review_request,
)


@freeze_time("2020-01-01")
@requests_mock.Mocker()
class KownslAPITests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        zaak_json = generate_oas_component("zrc", "schemas/Zaak", url=ZAAK_URL)
        cls.zaak = factory(Zaak, zaak_json)
        user_assignees = UserAssigneeFactory(
            **{
                "username": "some-other-author",
                "first_name": "Some Other First",
                "last_name": "Some Last",
                "full_name": "Some Other First Some Last",
            }
        )
        assigned_users2 = AssignedUsersFactory(
            **{
                "deadline": "2022-04-15",
                "user_assignees": [user_assignees],
                "group_assignees": [],
                "email_notification": False,
            }
        )
        cls.review_request = ReviewRequestFactory()
        cls.review_request["assignedUsers"].append(assigned_users2)
        cls.advice = AdviceFactory()
        cls.reviews_advice = ReviewsAdviceFactory()
        cls.reviews_advice["reviews"] = [cls.advice]

        cls.review_object = deepcopy(REVIEW_OBJECT)
        cls.review_object["data"] = cls.reviews_advice

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
        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
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

    def test_get_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[REVIEW_REQUEST_OBJECTTYPE])
        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([REVIEW_REQUEST_OBJECT]),
        )

        review_request = get_review_request(self.review_request["id"])
        self.assertEqual(str(review_request.id), self.review_request["id"])

    def test_get_reviews(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[REVIEW_OBJECTTYPE])
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
            json=REVIEW_REQUEST_OBJECT,
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
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[REVIEW_REQUEST_OBJECTTYPE])
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
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[REVIEW_REQUEST_OBJECTTYPE])
        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([REVIEW_REQUEST_OBJECT]),
        )

        review_requests = get_all_review_requests_for_zaak(self.zaak)
        request = review_requests[0]
        self.assertEqual(str(request.id), self.review_request["id"])

    @patch("zac.core.api.validators.validate_zaak_documents")
    def test_update_assigned_users_review_request(self, m, *mocks):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[REVIEW_REQUEST_OBJECTTYPE])

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
        }
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
        reviews_advice = ReviewsAdviceFactory()
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
                serializer = ConfigureReviewRequestSerializer(
                    data=data, context=context
                )
                serializer.is_valid(raise_exception=True)

        m.get(REVIEW_REQUEST_OBJECTTYPE["url"], json=REVIEW_REQUEST_OBJECTTYPE)
        m.get(
            REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION["url"],
            json=REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION,
        )

        m.patch(REVIEW_REQUEST_OBJECT["url"], json=REVIEW_REQUEST_OBJECT)

        with patch(
            "zac.contrib.objects.services.fetch_review_request",
            return_value=REVIEW_REQUEST_OBJECT,
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
                        "zaak": "https://zaken.nl/api/zaken/0c79c41d-72ef-4ea2-8c4c-03c9945da2a2",
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

        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[REVIEW_REQUEST_OBJECTTYPE])
        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([REVIEW_REQUEST_OBJECT]),
        )
        rr = deepcopy(REVIEW_REQUEST_OBJECT)
        rr["record"]["data"]["locked"] = True
        rr["record"]["data"]["lockReason"] = "some-reason"

        m.patch(REVIEW_REQUEST_OBJECT["url"], json=rr)

        review_request = lock_review_request(
            self.review_request["id"], lock_reason="some-reason"
        )
        self.assertEqual(str(review_request.id), self.review_request["id"])
        self.assertTrue(m.last_request.json()["record"]["data"]["locked"])
