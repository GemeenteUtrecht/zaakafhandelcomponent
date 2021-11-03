import datetime
import uuid

from django.test import TestCase
from django.utils import timezone

from zgw_consumers.api_models.base import factory

from zac.contrib.kownsl.data import Advice, Approval, ReviewRequest
from zac.utils.api_models import serialize


class ConvertToJsonTests(TestCase):
    def test_review_requests_for_advice(self):
        review_request_data = {
            "id": "45638aa6-e177-46cc-b580-43339795d5b5",
            "created": "2020-12-16T14:15:22Z",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "advice",
            "documents": [],
            "frontendUrl": f"https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
            "numAdvices": 1,
            "numApprovals": 0,
            "numAssignedUsers": 1,
            "toelichting": "Like a flash of light in an endless night.",
            "userDeadlines": {},
            "requester": "Henkie",
        }
        advice_data = {
            "created": "2020-06-17T10:21:16Z",
            "author": {
                "username": "foo",
                "firstName": "",
                "lastName": "",
            },
            "group": "",
            "advice": "dummy",
            "documents": [],
        }
        review_request = factory(ReviewRequest, review_request_data)
        advice = factory(Advice, advice_data)
        review_request.advices = [advice]
        review_requests = [review_request]

        result = serialize(review_requests)

        self.assertEqual(
            result,
            [
                {
                    "id": uuid.UUID("45638aa6-e177-46cc-b580-43339795d5b5"),
                    "created": timezone.make_aware(
                        datetime.datetime(2020, 12, 16, 14, 15, 22)
                    ),
                    "for_zaak": "https://zaken.nl/api/v1/zaak/123",
                    "review_type": "advice",
                    "documents": [],
                    "frontend_url": "https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
                    "num_advices": 1,
                    "num_approvals": 0,
                    "num_assigned_users": 1,
                    "toelichting": "Like a flash of light in an endless night.",
                    "advices": [
                        {
                            "created": timezone.make_aware(
                                datetime.datetime(2020, 6, 17, 10, 21, 16)
                            ),
                            "author": {
                                "username": "foo",
                                "first_name": "",
                                "last_name": "",
                            },
                            "group": "",
                            "advice": "dummy",
                            "documents": [],
                        }
                    ],
                    "user_deadlines": {},
                    "requester": "Henkie",
                }
            ],
        )

    def test_review_request_for_approval(self):
        review_request_data = {
            "id": "45638aa6-e177-46cc-b580-43339795d5b5",
            "created": "2020-12-16T14:15:22Z",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "advice",
            "documents": [],
            "frontendUrl": f"https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
            "numAdvices": 0,
            "numApprovals": 1,
            "numAssignedUsers": 1,
            "toelichting": "I pity the living, envy for the dead",
            "userDeadlines": {},
            "requester": "Henkie",
        }
        approval_data = {
            "created": "2020-06-17T10:21:16Z",
            "author": {
                "username": "foo",
                "firstName": "",
                "lastName": "",
            },
            "group": "",
            "approved": True,
            "toelichting": "I don't feel anything.",
        }
        review_request = factory(ReviewRequest, review_request_data)
        approval = factory(Approval, approval_data)
        review_request.approvals = [approval]
        review_requests = [review_request]

        result = serialize(review_requests)

        self.assertEqual(
            result,
            [
                {
                    "id": uuid.UUID("45638aa6-e177-46cc-b580-43339795d5b5"),
                    "created": timezone.make_aware(
                        datetime.datetime(2020, 12, 16, 14, 15, 22)
                    ),
                    "for_zaak": "https://zaken.nl/api/v1/zaak/123",
                    "review_type": "advice",
                    "documents": [],
                    "frontend_url": "https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
                    "num_advices": 0,
                    "num_approvals": 1,
                    "num_assigned_users": 1,
                    "toelichting": "I pity the living, envy for the dead",
                    "approvals": [
                        {
                            "created": timezone.make_aware(
                                datetime.datetime(2020, 6, 17, 10, 21, 16)
                            ),
                            "author": {
                                "username": "foo",
                                "first_name": "",
                                "last_name": "",
                            },
                            "group": "",
                            "approved": True,
                            "toelichting": "I don't feel anything.",
                        }
                    ],
                    "user_deadlines": {},
                    "requester": "Henkie",
                }
            ],
        )
