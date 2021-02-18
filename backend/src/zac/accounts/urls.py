from django.urls import path

from .views import (
    AuthorizationProfileCreateView,
    AuthorizationProfileDetailView,
    AuthorizationProfileListView,
    LoginView,
    PermissionSetCreateView,
    PermissionSetDetailView,
    PermissionSetsView,
    PermissionSetUpdateView,
    UserAuthorizationProfileCreateView,
)

app_name = "accounts"

urlpatterns = [
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
]
