from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views.generic import RedirectView

from mozilla_django_oidc_db.views import AdminLoginFailure

handler500 = "zac.utils.views.server_error"
handler403 = "zac.utils.views.permission_denied"

urlpatterns = [
    path("admin/hijack/", include("hijack.urls")),
    path("admin/", admin.site.urls),
    path("admin/login/failure/", AdminLoginFailure.as_view(), name="admin-oidc-error"),
    path("api/", include("zac.api.urls")),
    path("accounts/", include("zac.accounts.urls")),
    path("core/", include("zac.core.urls")),
    path("oidc/", include("mozilla_django_oidc.urls")),
    # path("ref/", include("vng_api_common.urls")),
    path("", RedirectView.as_view(url=settings.UI_ROOT_URL)),
]

# NOTE: The staticfiles_urlpatterns also discovers static files (ie. no need to run collectstatic). Both the static
# folder and the media folder are only served via Django if DEBUG = True.
urlpatterns += staticfiles_urlpatterns() + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
