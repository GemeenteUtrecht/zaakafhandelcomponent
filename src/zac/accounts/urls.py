from django.urls import include, path

from . import api
from .views import (
    AuthorizationProfileCreateView,
    AuthorizationProfileDetailView,
    AuthorizationProfileListView,
    LoginView,
    PermissionSetCreateView,
    PermissionSetDetailView,
    PermissionSetsView,
    PermissionSetUpdateView,
    RequestAccessCreateView,
    UserAuthorizationProfileCreateView,
)

app_name = "accounts"

urlpatterns = [
    path("api/", include(api)),
    path("login/", LoginView.as_view(), name="login"),
    path(
        "auth-profiles/",
        AuthorizationProfileListView.as_view(),
        name="authprofile-list",
    ),
    path(
        "auth-profiles/add/",
        AuthorizationProfileCreateView.as_view(),
        name="authprofile-create",
    ),
    path(
        "auth-profiles/<uuid:uuid>/",
        AuthorizationProfileDetailView.as_view(),
        name="authprofile-detail",
    ),
    path(
        "auth-profiles/<uuid:uuid>/add-user/",
        UserAuthorizationProfileCreateView.as_view(),
        name="authprofile-add-user",
    ),
    path("permission-sets/", PermissionSetsView.as_view(), name="permission-set-list"),
    path(
        "permission-sets/add/",
        PermissionSetCreateView.as_view(),
        name="permission-set-create",
    ),
    path(
        "permission-sets/<pk>/",
        PermissionSetDetailView.as_view(),
        name="permission-set-detail",
    ),
    path(
        "permission-sets/<pk>/change/",
        PermissionSetUpdateView.as_view(),
        name="permission-set-change",
    ),
    path(
        "request-accesses/zaken/<bronorganisatie>/<identificatie>/add",
        RequestAccessCreateView.as_view(),
        name="request-access-create",
    ),
]
