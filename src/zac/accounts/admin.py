from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Entitlement, PermissionSet, User, UserEntitlement


@admin.register(User)
class _UserAdmin(UserAdmin):
    pass


@admin.register(PermissionSet)
class PermissionSetAdmin(admin.ModelAdmin):
    list_display = ("name", "permissions", "zaaktype", "max_va")
    list_filter = ("max_va", "zaaktype")
    search_fields = ("name",)


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
    list_display = ("name",)
    list_filter = ("permission_sets",)
    search_fields = ("name", "uuid")


@admin.register(UserEntitlement)
class UserEntitlementAdmin(admin.ModelAdmin):
    list_display = ("user", "entitlement", "start", "end")
    list_filter = ("user", "entitlement", "start", "end")
    search_fields = ("user__usernamae", "entitlement__name", "entitlement__uuid")
