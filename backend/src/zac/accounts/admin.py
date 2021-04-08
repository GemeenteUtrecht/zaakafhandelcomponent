from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.urls import reverse
from django.utils.html import format_html_join
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


class UserAuthorizationProfileInline(admin.TabularInline):
    model = UserAuthorizationProfile
    extra = 1


@admin.register(User)
class _UserAdmin(HijackUserAdminMixin, UserAdmin):
    list_display = UserAdmin.list_display + ("hijack_field",)
    inlines = [UserAuthorizationProfileInline]
    filter_horizontal = ("groups", "user_permissions", "atomic_permissions")

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        return fieldsets + (
            (_("Object permissions"), {"fields": ("atomic_permissions",)}),
        )


class CheckboxSelectMultipleWithLinks(forms.CheckboxSelectMultiple):
    option_template_name = (
        "admin/accounts/authorizationprofile/checkbox_option_with_link.html"
    )

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        model = self.choices.queryset.model
        context.update({"opts": model._meta})
        return context


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
        return obj.blueprint_permissions.count()

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


@admin.register(AtomicPermission)
class AtomicPermissionAdmin(PermissionMixin, admin.ModelAdmin):
    list_display = ("permission", "object_type", "start_date")
    list_filter = ("permission", "object_type")
    search_fields = ("object_url",)


class AuthorizationProfileInline(admin.TabularInline):
    model = BlueprintPermission.auth_profiles.through
    extra = 1


class PolicyWidget(forms.Widget):
    template_name = "admin/accounts/blueprintpermission/policy_editor.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        json_schemas = {
            name: permission.blueprint_class.display_as_jsonschema()
            for name, permission in registry.items()
        }
        context.update({"json_schemas": json_schemas})
        return context


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
