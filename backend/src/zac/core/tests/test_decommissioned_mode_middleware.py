from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework.authtoken.models import Token

from zac.accounts.tests.factories import StaffUserFactory, SuperUserFactory, UserFactory
from zac.core.middleware import DECOMMISSIONED_CODE, DECOMMISSIONED_MESSAGE
from zac.core.models import CoreConfig
from zac.core.tests.utils import ClearCachesMixin


@override_settings(ROOT_URLCONF="zac.urls", AXES_ENABLED=False)
class DecommissionedModeMiddlewareTests(ClearCachesMixin, TestCase):
    def _set_mode(self, enabled: bool):
        config = CoreConfig.get_solo()
        config.decommissioned_mode = enabled
        config.save()

    def _assert_api_blocked(self, response):
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"detail": DECOMMISSIONED_MESSAGE, "code": DECOMMISSIONED_CODE},
        )

    def _assert_not_blocked(self, response):
        self.assertNotIn(DECOMMISSIONED_MESSAGE, response.content.decode())

    def test_user_not_blocked_when_disabled(self):
        self.client.force_login(UserFactory.create())

        self._assert_not_blocked(self.client.get("/api/ping/"))

    def test_user_blocked_on_api(self):
        self._set_mode(True)
        self.client.force_login(UserFactory.create())

        self._assert_api_blocked(self.client.get("/api/ping/"))
        self._assert_api_blocked(self.client.get("/api/accounts/users/me"))
        self._assert_api_blocked(self.client.post("/api/search/zaken"))

    def test_user_gets_white_page_outside_api(self):
        self._set_mode(True)
        self.client.force_login(UserFactory.create())

        # The UI redirects to "/" when the API reports the decommissioned code.
        for path in ("/", "/core/some/path"):
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 403)
                self.assertTemplateUsed(response, "core/decommissioned.html")
                self.assertContains(response, DECOMMISSIONED_MESSAGE, status_code=403)
                self.assertContains(
                    response,
                    'src="/ui/assets/images/gemeente-utrecht-logo.svg"',
                    status_code=403,
                )

    def test_staff_user_blocked_from_admin(self):
        self._set_mode(True)
        self.client.force_login(StaffUserFactory.create())

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "core/decommissioned.html")

    def test_superuser_passes(self):
        self._set_mode(True)
        self.client.force_login(SuperUserFactory.create())

        self._assert_not_blocked(self.client.get("/api/ping/"))
        response = self.client.get("/admin/core/coreconfig/")
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_turn_mode_off_in_admin_form(self):
        self._set_mode(True)
        self.client.force_login(SuperUserFactory.create())

        response = self.client.get("/admin/core/coreconfig/")

        self.assertContains(response, "decommissioned_mode")

    def test_hijacked_session_passes(self):
        self._set_mode(True)
        user = UserFactory.create()
        self.client.force_login(SuperUserFactory.create())

        self.client.post(reverse("hijack:acquire"), {"user_pk": user.pk})

        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        response = self.client.get("/api/ping/")
        self.assertEqual(response["X-Is-Hijacked"], "true")
        self._assert_not_blocked(response)

    def test_anonymous_requests_pass(self):
        self._set_mode(True)

        self._assert_not_blocked(self.client.get("/api/ping/"))
        self.assertEqual(self.client.get("/accounts/login/").status_code, 200)
        self.assertEqual(self.client.get("/admin/login/").status_code, 200)

    def test_token_requests_pass(self):
        self._set_mode(True)
        token = Token.objects.create(user=StaffUserFactory.create())

        response = self.client.post(
            "/api/core/management/cache/reset",
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

        self._assert_not_blocked(response)

    def test_login_paths_stay_reachable_for_logged_in_user(self):
        self._set_mode(True)
        self.client.force_login(UserFactory.create())

        for path in ("/accounts/login/", "/accounts/logged_in/", "/admin/login/"):
            with self.subTest(path=path):
                self._assert_not_blocked(self.client.get(path))

    def test_logout_stays_reachable(self):
        self._set_mode(True)
        self.client.force_login(UserFactory.create())

        self._assert_not_blocked(self.client.post("/api/accounts/logout"))

    def test_cache_invalidated_on_save(self):
        self.client.force_login(UserFactory.create())
        self._assert_not_blocked(self.client.get("/api/ping/"))

        self._set_mode(True)
        self._assert_api_blocked(self.client.get("/api/ping/"))

        self._set_mode(False)
        self._assert_not_blocked(self.client.get("/api/ping/"))
