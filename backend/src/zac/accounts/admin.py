from urllib.parse import urlencode

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from hijack_admin.admin import HijackUserAdminMixin

from .models import (
    AccessRequest,
    AtomicPermission,
    AuthorizationProfile,
    BlueprintPermission,
    User,
    UserAuthorizationProfile,
)
from .permissions import registry
from .widgets import CheckboxSelectMultipleWithLinks, PolicyWidget


class UserAuthorizationProfileInline(admin.TabularInline):
    model = UserAuthorizationProfile
    extra = 1


@admin.register(User)
class _UserAdmin(HijackUserAdminMixin, UserAdmin):
    list_display = UserAdmin.list_display + (
        "is_superuser",
        "get_auth_profiles_display",
        "get_atomic_permissions_display",
        "hijack_field",
    )
    inlines = [UserAuthorizationProfileInline]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        return fieldsets + (
            (_("Object permissions"), {"fields": ("atomic_permissions",)}),
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("atomic_permissions", "auth_profiles")
        )

    def display_related_as_list_of_links(self, obj, field_name):
        field = getattr(obj, field_name)

        # view_name = f"admin:{model._meta.app_label}_{model._meta.model_name}_change"
        return field

    def get_auth_profiles_display(self, obj):
        return format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            (
                (
                    reverse(
                        "admin:accounts_authorizationprofile_change",
                        args=[auth_profile.id],
                    ),
                    auth_profile.name,
                )
                for auth_profile in obj.auth_profiles.all()
            ),
        )

    get_auth_profiles_display.short_description = _("authorization profiles")

    def get_atomic_permissions_display(self, obj):
        count = obj.atomic_permissions.count()
        changelist_url = reverse("admin:accounts_atomicpermission_changelist")
        query = {"users__id__exact": obj.id}
        url = f"{changelist_url}?{urlencode(query)}"
        return format_html('<a href="{}">{}</a>', url, count)

    get_atomic_permissions_display.short_description = _("atomic permissions")


@admin.register(AuthorizationProfile)
class AuthorizationProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "get_blueprint_permissions_count", "get_users_display")
    list_filter = ("blueprint_permissions__permission",)
    search_fields = ("name", "uuid")
    inlines = (UserAuthorizationProfileInline,)
    formfield_overrides = {
        models.ManyToManyField: {"widget": CheckboxSelectMultipleWithLinks},
    }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("blueprint_permissions", "user_set")

    def get_users_display(self, obj):
        return format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            (
                (
                    reverse(
                        "admin:accounts_user_change",
                        args=[user.id],
                    ),
                    user.username,
                )
                for user in obj.user_set.all()
            ),
        )

    get_users_display.short_description = _("users")

    def get_blueprint_permissions_count(self, obj):
        count = obj.blueprint_permissions.count()
        changelist_url = reverse("admin:accounts_blueprintpermission_changelist")
        query = {"auth_profiles__id__exact": obj.id}
        url = f"{changelist_url}?{urlencode(query)}"
        return format_html('<a href="{}">{}</a>', url, count)

    get_blueprint_permissions_count.short_description = _("total permissions")


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


class UserAtomicInline(admin.TabularInline):
    model = AtomicPermission.users.through
    extra = 1


@admin.register(AtomicPermission)
class AtomicPermissionAdmin(PermissionMixin, admin.ModelAdmin):
    list_display = (
        "permission",
        "object_type",
        "object_uuid",
        "get_users_display",
        "start_date",
    )
    list_filter = ("permission", "object_type", "users")
    search_fields = ("object_url",)
    inlines = (UserAtomicInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("users")

    def get_users_display(self, obj):
        return format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            (
                (
                    reverse(
                        "admin:accounts_user_change",
                        args=[user.id],
                    ),
                    user.username,
                )
                for user in obj.users.all()
            ),
        )

    get_users_display.short_description = _("users")


class AuthorizationProfileInline(admin.TabularInline):
    model = BlueprintPermission.auth_profiles.through
    extra = 1


@admin.register(BlueprintPermission)
class BlueprintPermissionAdmin(PermissionMixin, admin.ModelAdmin):
    list_display = (
        "permission",
        "object_type",
        "get_policy_list_display",
        "get_auth_profiles_display",
    )
    list_filter = ("permission", "object_type", "auth_profiles")
    formfield_overrides = {JSONField: {"widget": PolicyWidget}}
    inlines = (AuthorizationProfileInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("auth_profiles")

    def get_policy_list_display(self, obj):
        blueprint_class = obj.get_blueprint_class()
        blueprint = blueprint_class(obj.policy)
        return blueprint.short_display()

    get_policy_list_display.short_description = _("policy")

    def get_auth_profiles_display(self, obj):
        return format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            (
                (
                    reverse(
                        "admin:accounts_authorizationprofile_change",
                        args=[auth_profile.id],
                    ),
                    auth_profile.name,
                )
                for auth_profile in obj.auth_profiles.all()
            ),
        )

    get_auth_profiles_display.short_description = _("authorization profiles")
