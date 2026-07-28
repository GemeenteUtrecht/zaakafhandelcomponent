from django.test import TestCase, override_settings

from zac.core.models import CoreConfig
from zac.core.tests.utils import ClearCachesMixin


@override_settings(ROOT_URLCONF="zac.urls")
class ReadOnlyModeMiddlewareTests(ClearCachesMixin, TestCase):
    def _enable_read_only_mode(self):
        config = CoreConfig.get_solo()
        config.read_only_mode = True
        config.save()

    def test_get_requests_always_allowed(self):
        self._enable_read_only_mode()

        response = self.client.get("/api/some/random/path")

        self.assertNotEqual(response.status_code, 503)

    def test_non_api_paths_are_never_blocked(self):
        self._enable_read_only_mode()

        response = self.client.post("/admin/login/")

        self.assertNotEqual(response.status_code, 503)

    def test_write_request_blocked_when_enabled(self):
        self._enable_read_only_mode()

        response = self.client.post("/api/some/random/path")

        self.assertEqual(response.status_code, 503)
        self.assertIn("detail", response.json())

    def test_write_request_allowed_when_disabled(self):
        config = CoreConfig.get_solo()
        config.read_only_mode = False
        config.save()

        response = self.client.post("/api/some/random/path")

        self.assertNotEqual(response.status_code, 503)

    def test_cache_invalidated_on_save(self):
        config = CoreConfig.get_solo()
        config.read_only_mode = False
        config.save()

        self.assertNotEqual(self.client.post("/api/some/random/path").status_code, 503)

        config.read_only_mode = True
        config.save()

        self.assertEqual(self.client.post("/api/some/random/path").status_code, 503)

    def test_explicitly_allowlisted_endpoints_are_not_blocked(self):
        self._enable_read_only_mode()

        allowlisted = [
            ("patch", "/api/accounts/access-requests/1"),
            ("post", "/api/accounts/auth-profiles"),
            ("put", "/api/accounts/auth-profiles/abc-uuid"),
            ("delete", "/api/accounts/auth-profiles/abc-uuid"),
            ("post", "/api/accounts/cases/access"),
            ("delete", "/api/accounts/cases/access/1"),
            ("put", "/api/accounts/cases/access/bulk_update"),
            ("post", "/api/accounts/groups"),
            ("put", "/api/accounts/groups/1"),
            ("delete", "/api/accounts/groups/1"),
            ("post", "/api/accounts/logout"),
            ("post", "/api/accounts/roles"),
            ("put", "/api/accounts/roles/1"),
            ("patch", "/api/accounts/roles/1"),
            ("delete", "/api/accounts/roles/1"),
            ("post", "/api/accounts/user-auth-profiles"),
            ("put", "/api/accounts/user-auth-profiles/1"),
            ("patch", "/api/accounts/user-auth-profiles/1"),
            ("delete", "/api/accounts/user-auth-profiles/1"),
            ("post", "/api/accounts/management/axes/reset"),
            ("post", "/api/core/management/anything"),
            ("post", "/api/checklists/management/anything"),
            ("post", "/api/search/management/anything"),
            ("post", "/api/activities/activities"),
            ("delete", "/api/activities/activities/1"),
            ("patch", "/api/core/recently-viewed"),
            ("post", "/api/core/rollen/medewerker/betrokkeneIdentificatie"),
            ("post", "/api/dashboard/management"),
            ("post", "/api/dashboard/management/summary"),
            ("post", "/api/core/objects"),
            ("post", "/api/search/cases/123456789/ZAAK-01/documents"),
            ("post", "/api/search/quick-search"),
            ("post", "/api/search/reports/"),
            ("put", "/api/search/reports/1/"),
            ("patch", "/api/search/reports/1/"),
            ("delete", "/api/search/reports/1/"),
            ("post", "/api/search/vgu-reports/informatieobjecten"),
            ("post", "/api/search/vgu-reports/zaken"),
            ("post", "/api/search/zaken"),
            ("post", "/api/workstack/summary"),
            ("post", "/api/dowc/123456789/ZAAK-01/read"),
        ]

        for method, path in allowlisted:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path)
                self.assertNotEqual(response.status_code, 503)

    def test_other_write_endpoints_still_blocked(self):
        self._enable_read_only_mode()

        blocked = [
            ("post", "/api/core/zaak-attachments"),
            ("delete", "/api/search/reports"),  # no trailing slash -> not allowlisted
            ("post", "/api/dashboard/boards"),
            ("post", "/api/dowc/123456789/ZAAK-01/write"),  # only "read" is allowlisted
        ]

        for method, path in blocked:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 503)
