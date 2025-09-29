from copy import deepcopy
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import StatusType, ZaakType
from zgw_consumers.api_models.zaken import Status
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.models import User
from zac.activities.tests.factories import ActivityFactory, ActivityStatuses
from zac.core.services import find_zaak, get_zaak
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get
from zgw.models.zrc import Zaak

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
    IDENTIFICATIE,
    STATUS,
    STATUS_RESPONSE,
    STATUSTYPE_RESPONSE,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKTYPE,
    ZAAKTYPE_RESPONSE,
    ZAKEN_ROOT,
)

# UPDATED: snake_case keys
NOTIFICATION = {
    "kanaal": "zaken",
    "hoofd_object": ZAAK,
    "resource": "status",
    "resource_url": STATUS,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "geheim",
    },
}


@requests_mock.Mocker()
class StatusCreatedTests(ESMixin, APITestCAse):
    """
    Test that the appropriate actions happen on status creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.ztc = Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        cls.zrc = Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client.force_authenticate(user=self.user)

    @patch("zac.core.services.fetch_zaaktype", return_value=None)
    def test_find_zaak_status_created(self, rm, *mocks):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)
        url = reverse("notifications:callback")

        with patch(
            "zac.core.services.get_paginated_results", return_value=[ZAAK_RESPONSE]
        ) as m:
            # populate cache
            find_zaak(BRONORGANISATIE, IDENTIFICATIE)

            response = self.client.post(url, NOTIFICATION)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            # second call should not hit the cache (because it was invalidated)
            find_zaak(BRONORGANISATIE, IDENTIFICATIE)
            self.assertEqual(m.call_count, 1)

    def test_get_zaak_status_created(self, rm, *mocks):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)

        url = reverse("notifications:callback")

        matrix = [
            {"zaak_uuid": "f3ff2713-2f53-42ff-a154-16842309ad60"},
            {"zaak_url": ZAAK},
            {"zaak_uuid": "f3ff2713-2f53-42ff-a154-16842309ad60", "zaak_url": ZAAK},
        ]

        for kwargs in matrix:
            with self.subTest(**kwargs):
                # populate cache
                get_zaak(**kwargs)
                self.assertEqual(rm.last_request.url, ZAAK)
                first_retrieve = rm.last_request

                response = self.client.post(url, NOTIFICATION)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

                num_calls_before = len(rm.request_history)

                # second call should re-fetch after invalidation
                get_zaak(**kwargs)

                self.assertEqual(rm.last_request.url, ZAAK)
                self.assertNotEqual(rm.last_request, first_retrieve)
                self.assertEqual(len(rm.request_history), num_calls_before + 1)

    def test_zaak_updated_is_closed(self, rm):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")

        zaak = deepcopy(ZAAK_RESPONSE)
        zaak["status"] = STATUS

        mock_resource_get(rm, zaak)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        statustype = deepcopy(STATUSTYPE_RESPONSE)
        statustype["is_eindstatus"] = True
        mock_resource_get(rm, statustype)

        url = reverse("notifications:callback")

        activity = ActivityFactory.create(
            zaak=zaak["url"], status=ActivityStatuses.on_going
        )
        task = MagicMock()
        task.id = "some-id"

        # UPDATED: patch where these functions are imported & used now
        with patch(
            "zac.notifications.handlers.zaken.bulk_lock_review_requests_for_zaak"
        ) as mock_bulk_lock_rr_for_zaak, patch(
            "zac.notifications.handlers.zaken.bulk_close_all_documents_for_zaak"
        ) as mock_bulk_close_all_documents_for_zaak, patch(
            "zac.notifications.handlers.zaken.lock_checklist_for_zaak"
        ) as mock_lock_checklist_for_zaak, patch(
            "zac.notifications.handlers.zaken.get_camunda_user_tasks",
            return_value=[task],
        ) as mock_get_camunda_user_tasks, patch(
            "zac.notifications.handlers.zaken.complete_task"
        ) as mock_complete_task:
            response = self.client.post(url, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        mock_bulk_lock_rr_for_zaak.assert_called_once()
        mock_bulk_close_all_documents_for_zaak.assert_called_once()
        mock_lock_checklist_for_zaak.assert_called_once()
        mock_get_camunda_user_tasks.assert_called_once_with(
            payload={
                "name": settings.CAMUNDA_OPEN_BIJDRAGE_TASK_NAME + zaak["identificatie"]
            }
        )
        mock_complete_task.assert_called_with("some-id", variables=dict())

        activity.refresh_from_db()
        self.assertEqual(activity.status, ActivityStatuses.finished)
        self.assertIsNone(activity.user_assignee)
        self.assertIsNone(activity.group_assignee)
