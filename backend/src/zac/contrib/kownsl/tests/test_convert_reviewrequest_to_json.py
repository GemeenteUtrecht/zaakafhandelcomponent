import datetime
import uuid

from django.test import TestCase
from django.utils import timezone

from zgw_consumers.api_models.base import factory

from zac.contrib.kownsl.constants import KownslTypes
from zac.contrib.kownsl.data import Advice, Approval, ReviewRequest
from zac.utils.api_models import serialize

from .utils import ADVICE, APPROVAL, REVIEW_REQUEST


class ConvertToJsonTests(TestCase):
    maxDiff = None

    def test_review_requests_for_advice(self):
        review_request = factory(ReviewRequest, REVIEW_REQUEST)
        advice = factory(Advice, ADVICE)
        review_request.advices = [advice]
        review_requests = [review_request]
        result = serialize(review_requests)
        self.assertEqual(
            result,
            [
                {
                    "id": uuid.UUID(REVIEW_REQUEST["id"]),
                    "assigned_users": REVIEW_REQUEST["assignedUsers"],
                    "created": timezone.make_aware(
                        datetime.datetime(2022, 4, 14, 15, 49, 9, 830235)
                    ),
                    "for_zaak": REVIEW_REQUEST["forZaak"],
                    "review_type": REVIEW_REQUEST["reviewType"],
                    "documents": [],
                    "frontend_url": REVIEW_REQUEST["frontendUrl"],
                    "num_advices": REVIEW_REQUEST["numAdvices"],
                    "num_approvals": REVIEW_REQUEST["numApprovals"],
                    "num_assigned_users": REVIEW_REQUEST["numAssignedUsers"],
                    "toelichting": REVIEW_REQUEST["toelichting"],
                    "advices": [
                        {
                            "created": timezone.make_aware(
                                datetime.datetime(2022, 4, 14, 15, 50, 9, 830235)
                            ),
                            "author": {
                                "first_name": ADVICE["author"]["firstName"],
                                "last_name": ADVICE["author"]["lastName"],
                                "full_name": ADVICE["author"]["fullName"],
                                "username": ADVICE["author"]["username"],
                            },
                            "group": ADVICE["group"],
                            "advice": ADVICE["advice"],
                            "documents": [
                                {
                                    "document": ADVICE["documents"][0]["document"],
                                    "advice_version": ADVICE["documents"][0][
                                        "adviceVersion"
                                    ],
                                    "source_version": ADVICE["documents"][0][
                                        "sourceVersion"
                                    ],
                                }
                            ],
                        }
                    ],
                    "user_deadlines": REVIEW_REQUEST["userDeadlines"],
                    "requester": {
                        "first_name": REVIEW_REQUEST["requester"]["firstName"],
                        "last_name": REVIEW_REQUEST["requester"]["lastName"],
                        "full_name": REVIEW_REQUEST["requester"]["fullName"],
                        "username": REVIEW_REQUEST["requester"]["username"],
                    },
                    "locked": REVIEW_REQUEST["locked"],
                    "lock_reason": REVIEW_REQUEST["lockReason"],
                    "open_reviews": [
                        {
                            "deadline": datetime.date(2022, 4, 15),
                            "users": ["user:some-other-author"],
                            "groups": [],
                        }
                    ],
                    "metadata": {
                        "task_definition_id": REVIEW_REQUEST["metadata"][
                            "taskDefinitionId"
                        ],
                        "process_instance_id": REVIEW_REQUEST["metadata"][
                            "processInstanceId"
                        ],
                    },
                }
            ],
        )

    def test_review_request_for_approval(self):
        review_request = factory(
            ReviewRequest,
            {
                **REVIEW_REQUEST,
                "reviewType": KownslTypes.approval,
                "numAdvices": 0,
                "numApprovals": 1,
            },
        )
        approval = factory(Approval, APPROVAL)
        review_request.approvals = [approval]
        review_requests = [review_request]

        result = serialize(review_requests)
        self.assertEqual(
            result,
            [
                {
                    "id": uuid.UUID(REVIEW_REQUEST["id"]),
                    "assigned_users": REVIEW_REQUEST["assignedUsers"],
                    "created": timezone.make_aware(
                        datetime.datetime(2022, 4, 14, 15, 49, 9, 830235)
                    ),
                    "for_zaak": REVIEW_REQUEST["forZaak"],
                    "review_type": KownslTypes.approval,
                    "documents": [],
                    "frontend_url": REVIEW_REQUEST["frontendUrl"],
                    "num_advices": 0,
                    "num_approvals": 1,
                    "num_assigned_users": REVIEW_REQUEST["numAssignedUsers"],
                    "toelichting": REVIEW_REQUEST["toelichting"],
                    "approvals": [
                        {
                            "created": timezone.make_aware(
                                datetime.datetime(2022, 4, 14, 15, 51, 9, 830235)
                            ),
                            "author": {
                                "first_name": APPROVAL["author"]["firstName"],
                                "last_name": APPROVAL["author"]["lastName"],
                                "full_name": APPROVAL["author"]["fullName"],
                                "username": APPROVAL["author"]["username"],
                            },
                            "group": APPROVAL["group"],
                            "approved": APPROVAL["approved"],
                            "toelichting": APPROVAL["toelichting"],
                        }
                    ],
                    "user_deadlines": REVIEW_REQUEST["userDeadlines"],
                    "requester": {
                        "first_name": REVIEW_REQUEST["requester"]["firstName"],
                        "last_name": REVIEW_REQUEST["requester"]["lastName"],
                        "full_name": REVIEW_REQUEST["requester"]["fullName"],
                        "username": REVIEW_REQUEST["requester"]["username"],
                    },
                    "locked": REVIEW_REQUEST["locked"],
                    "lock_reason": REVIEW_REQUEST["lockReason"],
                    "open_reviews": [
                        {
                            "deadline": datetime.date(2022, 4, 15),
                            "users": ["user:some-other-author"],
                            "groups": [],
                        }
                    ],
                    "metadata": {
                        "task_definition_id": REVIEW_REQUEST["metadata"][
                            "taskDefinitionId"
                        ],
                        "process_instance_id": REVIEW_REQUEST["metadata"][
                            "processInstanceId"
                        ],
                    },
                }
            ],
        )
