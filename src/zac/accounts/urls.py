from django.urls import path

from .views import (
    AuthorizationProfileDetailView,
    AuthorizationProfileListView,
    LoginView,
    PermissionSetCreateView,
    PermissionSetsView,
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
        "auth-profiles/<uuid>/",
        AuthorizationProfileDetailView.as_view(),
        name="authprofile-detail",
    ),
    path("permission-sets/", PermissionSetsView.as_view(), name="permission-set-list"),
    path(
        "permission-sets/add/",
        PermissionSetCreateView.as_view(),
        name="permission-set-create",
    ),
]
