from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from hijack_admin.admin import HijackUserAdminMixin

from .models import (
    AccessRequest,
    AuthorizationProfile,
    BlueprintPermission,
    PermissionDefinition,
    User,
    UserAuthorizationProfile,
)
from .permissions import registry


class UserAuthorizationProfileInline(admin.TabularInline):
    model = UserAuthorizationProfile
    extra = 1


@admin.register(User)
class _UserAdmin(HijackUserAdminMixin, UserAdmin):
    list_display = UserAdmin.list_display + ("hijack_field",)
    inlines = [UserAuthorizationProfileInline]
    filter_horizontal = ("groups", "user_permissions", "permission_definitions")

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        return fieldsets + (
            (_("Object permissions"), {"fields": ("permission_definitions",)}),
        )


@admin.register(AuthorizationProfile)
class AuthorizationProfileAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name", "uuid")
    filter_horizontal = ("blueprint_permissions",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("blueprint_permissions")


@admin.register(UserAuthorizationProfile)
class UserAuthorizationProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "auth_profile", "start", "end")
    list_filter = ("user", "auth_profile", "start", "end")
    search_fields = ("user__username", "auth_profile__name", "auth_profile__uuid")


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ("requester", "result", "handler")
    list_filter = ("requester", "result")
    search_fields = ("requester__username", "zaak")
    raw_id_fields = ("requester", "handler")


class PermissionMixin:
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "permission":
            permission_choices = [(name, name) for name, permission in registry.items()]
            permission_choices.insert(0, ("", "---------"))
            return forms.ChoiceField(
                label=db_field.verbose_name.capitalize(),
                widget=forms.Select,
                choices=permission_choices,
                help_text=db_field.help_text,
            )

        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(PermissionDefinition)
class PermissionDefinitionAdmin(PermissionMixin, admin.ModelAdmin):
    list_display = ("permission", "object_type", "start_date")
    list_filter = ("permission", "object_type")
    search_fields = ("object_url",)


@admin.register(BlueprintPermission)
class BlueprintPermissionAdmin(PermissionMixin, admin.ModelAdmin):
    list_display = ("permission", "object_type", "start_date")
    list_filter = ("permission", "object_type")
    readonly_fields = ("display_policy_schema",)

    def display_policy_schema(self, obj):
        if obj.permission:
            blueprint_class = obj.get_blueprint_class()
            if blueprint_class:
                return blueprint_class.display_as_yaml()
        return ""

    display_policy_schema.short_description = _("policy schema")
