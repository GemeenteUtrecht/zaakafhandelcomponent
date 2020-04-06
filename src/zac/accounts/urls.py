from django.urls import path

from .views import (
    EntitlementsView,
    LoginView,
    PermissionSetCreateView,
    PermissionSetsView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("entitlements/", EntitlementsView.as_view(), name="entitlement-list"),
    path("permission-sets/", PermissionSetsView.as_view(), name="permission-set-list"),
    path(
        "permission-sets/add/",
        PermissionSetCreateView.as_view(),
        name="permission-set-create",
    ),
]
