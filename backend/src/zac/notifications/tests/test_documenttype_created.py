from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.models import User
from zac.core.services import get_informatieobjecttypen
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response

CATALOGUS = "https://some.ztc.nl/api/v1/catalogi/661ff970-6af0-46cf-a228-2c35639ad77e"

NOTIFICATION = {
    "kanaal": "informatieobjecttypen",
    "hoofdObject": "https://some.ztc.nl/api/v1/informatieobjecttypen/f3ff2713-2f53-42ff-a154-16842309ad60",
    "resource": "informatieobjecttype",
    "resourceUrl": "https://some.ztc.nl/api/v1/informatieobjecttypen/f3ff2713-2f53-42ff-a154-16842309ad60",
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {"catalogus": CATALOGUS},
}


@requests_mock.Mocker()
class informatieobjecttypeCreatedTests(ClearCachesMixin, APITestCase):
    """
    Test that the appropriate actions happen on zaak-creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.ztc = Service.objects.create(
            api_root="https://some.ztc.nl/api/v1/", api_type=APITypes.ztc
        )

    def setUp(self):
        super().setUp()

        self.client.force_authenticate(user=self.user)

    def test_informatieobjecttype_created_invalidate_list_cache(self, m):
        mock_service_oas_get(m, "https://some.ztc.nl/api/v1/", "ztc")
        m.get(
            f"https://some.ztc.nl/api/v1/informatieobjecttypen?catalogus={CATALOGUS}",
            json=paginated_response([]),
        )

        # call to populate cache
        informatieobjecttypen1 = get_informatieobjecttypen(catalogus=CATALOGUS)

        # post the notification
        response = self.client.post(reverse("notifications:callback"), NOTIFICATION)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # second call should not hit the cache
        informatieobjecttypen2 = get_informatieobjecttypen(catalogus=CATALOGUS)
        self.assertEqual(m.call_count, 3)  # 1 call for API spec
        self.assertEqual(
            m.request_history[1].url,
            m.request_history[2].url,
        )
