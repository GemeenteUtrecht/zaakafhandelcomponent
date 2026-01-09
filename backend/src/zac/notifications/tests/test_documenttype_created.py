from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.models import User
from zac.core.services import get_informatieobjecttypen
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import mock_service_oas_get
from zac.tests.utils import paginated_response

from .utils import CATALOGI_ROOT, CATALOGUS

NOTIFICATION = {
    "kanaal": "informatieobjecttypen",
    "hoofd_object": f"{CATALOGI_ROOT}informatieobjecttypen/f3ff2713-2f53-42ff-a154-16842309ad60",
    "resource": "informatieobjecttype",
    "resource_url": f"{CATALOGI_ROOT}informatieobjecttypen/f3ff2713-2f53-42ff-a154-16842309ad60",
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {"catalogus": CATALOGUS},
}


@requests_mock.Mocker()
class informatieobjecttypeCreatedTests(ClearCachesMixin, APITestCase):
    """
    Test that the appropriate actions happen on informatieobjecttype-creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.ztc = Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_informatieobjecttype_created_invalidate_list_cache(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}informatieobjecttypen?catalogus={CATALOGUS}",
            json=paginated_response([]),
        )

        # call to populate cache
        get_informatieobjecttypen(catalogus=CATALOGUS)

        # post the notification
        response = self.client.post(reverse("notifications:callback"), NOTIFICATION)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # second call should re-fetch (cache invalidated)
        get_informatieobjecttypen(catalogus=CATALOGUS)

        # 1 call for API spec + 2 identical list calls (before and after invalidation)
        self.assertEqual(m.call_count, 3)
        self.assertEqual(
            m.request_history[1].url,
            m.request_history[2].url,
        )
