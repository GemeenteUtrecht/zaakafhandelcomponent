from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.models import User
from zac.core.services import get_zaaktypen
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import mock_service_oas_get
from zac.tests.utils import paginated_response

from .utils import CATALOGI_ROOT, CATALOGUS, ZAAKTYPE

# UPDATED: snake_case keys
NOTIFICATION = {
    "kanaal": "zaaktypen",
    "hoofd_object": ZAAKTYPE,
    "resource": "zaaktype",
    "resource_url": ZAAKTYPE,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {"catalogus": CATALOGUS},
}


@requests_mock.Mocker()
class ZaakTypeCreatedTests(ClearCachesMixin, APITestCase):
    """
    Test that the appropriate actions happen on zaak-creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.ztc = Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_zaaktype_created_invalidate_list_cache(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS}",
            json=paginated_response([]),
        )

        # call to populate cache
        get_zaaktypen(catalogus=CATALOGUS)

        # post the notification
        response = self.client.post(reverse("notifications:callback"), NOTIFICATION)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # second call should not hit the cache
        get_zaaktypen(catalogus=CATALOGUS)
        self.assertEqual(m.call_count, 3)  # 1 call for API spec
        self.assertEqual(
            m.request_history[1].url,
            m.request_history[2].url,
        )

    def test_zaaktype_created_invalidated_catalogusless_cache(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([]),
        )

        # call to populate cache
        get_zaaktypen()

        # post the notification
        response = self.client.post(reverse("notifications:callback"), NOTIFICATION)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # second call should not hit the cache
        get_zaaktypen()
        self.assertEqual(m.call_count, 3)  # 1 call for API spec
        self.assertEqual(
            m.request_history[1].url,
            m.request_history[2].url,
        )
