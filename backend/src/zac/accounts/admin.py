from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from hijack_admin.admin import HijackUserAdminMixin

from .models import (
    AccessRequest,
    AuthorizationProfile,
    InformatieobjecttypePermission,
    PermissionDefinition,
    PermissionSet,
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


@admin.register(PermissionSet)
class PermissionSetAdmin(admin.ModelAdmin):
    list_display = ("name", "permissions", "zaaktype_identificaties", "max_va")
    list_filter = ("max_va",)
    search_fields = ("name",)


@admin.register(InformatieobjecttypePermission)
class InformatieobjecttypePermissionAdmin(admin.ModelAdmin):
    list_display = ("omschrijving", "catalogus", "max_va")
    list_filter = ("omschrijving", "catalogus", "max_va", "permission_set")
    search_fields = ("omschrijving", "catalogus", "max_va")
    raw_id_fields = ("permission_set",)


@admin.register(AuthorizationProfile)
class AuthorizationProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "display_permission_sets", "oo")
    list_filter = ("permission_sets", "oo")
    search_fields = ("name", "uuid")
    filter_horizontal = ("permission_sets",)
    autocomplete_fields = ("oo",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("permission_sets")

    def display_permission_sets(self, obj):
        perm_sets = obj.permission_sets.all()
        return ", ".join([perm_set.name for perm_set in perm_sets])

    display_permission_sets.short_description = _("permission sets")


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


@admin.register(PermissionDefinition)
class PermissionDefinitionAdmin(admin.ModelAdmin):
    list_display = ("permission", "object_type", "start_date", "display_is_atomic")
    list_filter = ("permission", "object_type")
    search_fields = ("object_url",)
    readonly_fields = ("display_policy_schema",)

    def display_is_atomic(self, obj):
        return bool(obj.object_url)

    display_is_atomic.boolean = True
    display_is_atomic.short_description = _("is atomic")

    def display_policy_schema(self, obj):
        if obj.permission:
            blueprint_class = obj.get_blueprint_class()
            if blueprint_class:
                return blueprint_class.display_as_yaml()
        return ""

    display_policy_schema.short_description = _("policy schema")

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
