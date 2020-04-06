from django.urls import path

from .views import EntitlementsView, LoginView, PermissionSetsView

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("entitlements/", EntitlementsView.as_view(), name="entitlement-list"),
    path("permission-sets/", PermissionSetsView.as_view(), name="permission-set-list"),
]
