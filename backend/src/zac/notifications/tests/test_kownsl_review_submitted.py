# from unittest.mock import patch

# from django.core.cache import cache
# from django.urls import reverse_lazy

# import requests_mock
# from rest_framework import status
# from rest_framework.test import APITestCase
# from zgw_consumers.api_models.base import factory
# from zgw_consumers.constants import APITypes
# from zgw_consumers.models import APITypes, Service
# from zgw_consumers.test import generate_oas_component

# from zac.accounts.tests.factories import UserFactory
# from zac.contrib.objects.kownsl.api import get_review_request
# from zac.contrib.objects.kownsl.tests.utils import (
#     REVIEW_REQUEST,
#     ZAKEN_ROOT,
# )
# from zac.core.tests.utils import ClearCachesMixin
# from zgw.models.zrc import Zaak

# RR_URL = f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}"
# NOTIFICATION = {
#     "kanaal": "kownsl",
#     "hoofdObject": RR_URL,
#     "resource": "reviewRequest",
#     "resourceUrl": RR_URL,
#     "actie": "reviewSubmitted",
#     "aanmaakdatum": "2020-11-04T15:24:00+00:00",
#     "kenmerken": {"author": "bob", "group": ""},
# }

# TASK_DATA = {
#     "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
#     "name": "aName",
#     "assignee": None,
#     "created": "2013-01-23T13:42:42.000+0200",
#     "due": "2013-01-23T13:49:42.576+0200",
#     "followUp": "2013-01-23T13:44:42.437+0200",
#     "delegationState": "RESOLVED",
#     "description": "aDescription",
#     "executionId": "anExecution",
#     "owner": "anOwner",
#     "parentTaskId": None,
#     "priority": 42,
#     "processDefinitionId": "aProcDefId",
#     "processInstanceId": REVIEW_REQUEST["metadata"]["processInstanceId"],
#     "caseDefinitionId": "aCaseDefId",
#     "caseInstanceId": "aCaseInstId",
#     "caseExecutionId": "aCaseExecution",
#     "taskDefinitionKey": "aTaskDefinitionKey",
#     "suspended": False,
#     "formKey": "",
#     "tenantId": "aTenantId",
# }


# @requests_mock.Mocker()
# class ReviewSubmittedTests(ClearCachesMixin, APITestCase):
#     """
#     Test the correct behaviour when reviews are submitted.

#     """

#     endpoint = reverse_lazy("notifications:kownsl-callback")

#     @classmethod
#     def setUpTestData(cls):
#         cls.user = UserFactory.create(username="notifs")

#     def setUp(self):
#         super().setUp()

#         self.client.force_authenticate(user=self.user)

#     @patch(
#         "zac.contrib.objects.kownsl.views.invalidate_review_requests_cache",
#         return_value=None,
#     )
#     def test_user_task_closed(self, m, mock_invalidate_cache):

#         m.get(
#             RR_URL,
#             json=REVIEW_REQUEST,
#         )
#         m.get(
#             f"https://camunda.example.com/engine-rest/task?processInstanceId={REVIEW_REQUEST['metadata']['processInstanceId']}&taskDefinitionKey={REVIEW_REQUEST['metadata']['taskDefinitionId']}&assignee=user%3Abob",
#             json=[{**TASK_DATA, "assignee": f"user:bob"}],
#         )
#         m.post(
#             f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/complete",
#             json={"variables": {}},
#         )

#         response = self.client.post(self.endpoint, NOTIFICATION)

#         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

#         self.assertEqual(m.last_request.method, "POST")
#         self.assertEqual(
#             m.last_request.url,
#             f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/complete",
#         )

#     @patch("zac.contrib.objects.kownsl.cache.get_zaak")
#     def test_review_submitted_clears_cache(self, m, mock_get_zaak):
#         Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
#         zaak = generate_oas_component("zrc", "schemas/Zaak", url=REVIEW_REQUEST["zaak"])
#         mock_get_zaak = factory(Zaak, zaak)

#         m.get(
#             RR_URL,
#             json=REVIEW_REQUEST,
#         )
#         m.get(
#             f"https://camunda.example.com/engine-rest/task?processInstanceId={REVIEW_REQUEST['metadata']['processInstanceId']}&taskDefinitionKey={REVIEW_REQUEST['metadata']['taskDefinitionId']}&assignee=user%3Abob",
#             json=[{**TASK_DATA, "assignee": f"user:bob"}],
#         )
#         m.post(
#             f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/complete",
#             json={"variables": {}},
#         )

#         # create users
#         UserFactory.create(username="some-author")
#         UserFactory.create(username="some-other-author")
#         # Fill cache
#         get_review_request(REVIEW_REQUEST["id"])
#         self.assertTrue(cache.has_key(f"review_request:detail:{REVIEW_REQUEST['id']}"))

#         response = self.client.post(self.endpoint, NOTIFICATION)
#         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

#         self.assertFalse(cache.has_key(f"review_request:detail:{REVIEW_REQUEST['id']}"))

#     @patch(
#         "zac.contrib.objects.kownsl.views.invalidate_review_requests_cache",
#         return_value=None,
#     )
#     def test_no_user_tasks_found(self, m, mock_invalidate_cache):
#         """
#         Assert that the notification is succesfully handled even if the user task is
#         already closed.

#         This can happen because of the `returnUrl` action.
#         """

#         m.get(
#             RR_URL,
#             json=REVIEW_REQUEST,
#         )

#         m.get(
#             f"https://camunda.example.com/engine-rest/task?processInstanceId={REVIEW_REQUEST['metadata']['processInstanceId']}&taskDefinitionKey={REVIEW_REQUEST['metadata']['taskDefinitionId']}&assignee=user%3Abob",
#             json=[],
#         )

#         with patch(
#             "zac.contrib.objects.kownsl.views.set_assignee_and_complete_task"
#         ) as mock_complete:
#             response = self.client.post(self.endpoint, NOTIFICATION)

#         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

#         self.assertEqual(m.last_request.method, "GET")
#         mock_complete.assert_not_called()

#     @patch(
#         "zac.contrib.objects.kownsl.views.invalidate_review_requests_cache",
#         return_value=None,
#     )
#     def test_user_task_closed_group_assignee_still_sets_a_user_assignee(
#         self, m, mock_invalidate_cache
#     ):

#         m.get(
#             RR_URL,
#             json=REVIEW_REQUEST,
#         )

#         m.get(
#             f"https://camunda.example.com/engine-rest/task?processInstanceId={REVIEW_REQUEST['metadata']['processInstanceId']}&taskDefinitionKey={REVIEW_REQUEST['metadata']['taskDefinitionId']}&assignee=group%3Asome-group",
#             json=[{**TASK_DATA, "assignee": "group:some-group"}],
#         )
#         m.post(
#             f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/assignee",
#             status_code=204,
#         )
#         m.post(
#             f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/complete",
#             json={"variables": {}},
#         )

#         response = self.client.post(
#             self.endpoint,
#             {**NOTIFICATION, "kenmerken": {"author": "bob", "group": "some-group"}},
#         )

#         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

#         self.assertEqual(m.last_request.method, "POST")
#         self.assertEqual(
#             m.last_request.url,
#             f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/complete",
#         )
