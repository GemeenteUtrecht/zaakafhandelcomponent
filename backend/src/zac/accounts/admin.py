from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as _GroupAdmin, UserAdmin
from django.contrib.auth.models import Group
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _

from hijack.contrib.admin import HijackUserAdminMixin
from import_export.admin import ExportActionMixin, ImportMixin
from import_export.tmp_storages import CacheStorage
from nested_admin import NestedModelAdminMixin, NestedTabularInline

from zac.utils.admin import RelatedLinksMixin

from .forms import GroupAdminForm
from .models import (
    AccessRequest,
    ApplicationToken,
    ApplicationTokenAuthorizationProfile,
    AtomicPermission,
    AuthorizationProfile,
    BlueprintPermission,
    Role,
    User,
    UserAuthorizationProfile,
)
from .permissions import registry
from .resources import (
    AuthorizationProfileResource,
    BlueprintPermissionResource,
    RoleResource,
    UserAuthorizationProfileResource,
    UserResource,
)
from .widgets import PolicyWidget


class UserAuthorizationProfileInline(admin.TabularInline):
    model = UserAuthorizationProfile
    extra = 1


@admin.register(User)
class _UserAdmin(
    ImportMixin, ExportActionMixin, RelatedLinksMixin, HijackUserAdminMixin, UserAdmin
):
    tmp_storage_class = CacheStorage
    resource_class = UserResource

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "manages_groups",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    list_display = UserAdmin.list_display + (
        "is_superuser",
        "get_auth_profiles_display",
        "get_atomic_permissions_display",
    )
    inlines = [UserAuthorizationProfileInline]

    filter_horizontal = UserAdmin.filter_horizontal + ("manages_groups",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("atomic_permissions", "auth_profiles", "manages_groups")
        )

    def get_auth_profiles_display(self, obj):
        return self.display_related_as_list_of_links(obj, "auth_profiles")

    get_auth_profiles_display.short_description = _("authorization profiles")

    def get_atomic_permissions_display(self, obj):
        return self.display_related_as_count_with_link(obj, "atomic_permissions")

    get_atomic_permissions_display.short_description = _("atomic permissions")


@admin.register(AuthorizationProfile)
class AuthorizationProfileAdmin(
    ImportMixin, ExportActionMixin, RelatedLinksMixin, admin.ModelAdmin
):
    tmp_storage_class = CacheStorage
    list_display = ("name", "get_blueprint_permissions_count", "get_users_display")
    list_filter = ("blueprint_permissions__role",)
    search_fields = ("name", "uuid")
    inlines = (UserAuthorizationProfileInline,)
    filter_horizontal = ("blueprint_permissions",)
    resource_class = AuthorizationProfileResource

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("blueprint_permissions", "user_set")

    def get_users_display(self, obj):
        return self.display_related_as_list_of_links(obj, "user_set")

    get_users_display.short_description = _("users")

    def get_blueprint_permissions_count(self, obj):
        return self.display_related_as_count_with_link(obj, "blueprint_permissions")

    get_blueprint_permissions_count.short_description = _("total permissions")


@admin.register(UserAuthorizationProfile)
class UserAuthorizationProfileAdmin(ImportMixin, ExportActionMixin, admin.ModelAdmin):
    tmp_storage_class = CacheStorage
    list_display = ("user", "auth_profile", "start", "end")
    list_filter = ("user", "auth_profile", "start", "end")
    search_fields = ("user__username", "auth_profile__name", "auth_profile__uuid")
    resource_class = UserAuthorizationProfileResource


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
class AtomicPermissionAdmin(PermissionMixin, RelatedLinksMixin, admin.ModelAdmin):
    list_display = (
        "permission",
        "object_type",
        "object_uuid",
        "get_users_display",
    )
    list_filter = ("permission", "object_type", "users")
    search_fields = ("object_url",)
    inlines = (UserAtomicInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("users")

    def get_users_display(self, obj):
        return self.display_related_as_list_of_links(obj, "users")

    get_users_display.short_description = _("users")


class AuthorizationProfileInline(admin.TabularInline):
    model = BlueprintPermission.auth_profiles.through
    extra = 1


@admin.register(BlueprintPermission)
class BlueprintPermissionAdmin(
    ImportMixin, ExportActionMixin, RelatedLinksMixin, admin.ModelAdmin
):
    tmp_storage_class = CacheStorage
    resource_class = BlueprintPermissionResource
    list_display = (
        "hashkey",
        "role",
        "object_type",
        "get_policy_list_display",
        "get_auth_profiles_display",
    )
    list_filter = ("role", "object_type", "auth_profiles")
    formfield_overrides = {JSONField: {"widget": PolicyWidget}}
    inlines = (AuthorizationProfileInline,)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("role")
            .prefetch_related("auth_profiles")
        )

    def get_policy_list_display(self, obj):
        blueprint_class = obj.get_blueprint_class()
        blueprint = blueprint_class(obj.policy)
        return blueprint.short_display()

    get_policy_list_display.short_description = _("policy")

    def get_auth_profiles_display(self, obj):
        return self.display_related_as_list_of_links(obj, "auth_profiles")

    get_auth_profiles_display.short_description = _("authorization profiles")


@admin.register(Role)
class RoleAdmin(ImportMixin, ExportActionMixin, RelatedLinksMixin, admin.ModelAdmin):
    list_display = ("name", "permissions", "get_blueprint_permissions_display")
    resource_class = RoleResource
    tmp_storage_class = CacheStorage

    def get_blueprint_permissions_display(self, obj):
        return self.display_related_as_count_with_link(obj, "blueprint_permissions")

    get_blueprint_permissions_display.short_description = _("total permissions")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "permissions":
            permission_choices = [(name, name) for name, permission in registry.items()]
            return forms.MultipleChoiceField(
                label=db_field.verbose_name.capitalize(),
                widget=forms.SelectMultiple,
                choices=permission_choices,
                help_text=db_field.help_text,
            )

        return super().formfield_for_dbfield(db_field, request, **kwargs)


# Unregister old GroupAdmin
admin.site.unregister(Group)


# Register new GroupAdmin
@admin.register(Group)
class GroupAdmin(_GroupAdmin):
    form = GroupAdminForm

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("user_set")


class ApplicationTokenAuthorizationInline(NestedTabularInline):
    model = ApplicationTokenAuthorizationProfile
    extra = 0


@admin.register(ApplicationTokenAuthorizationProfile)
class ApplicationAuthorizationProfileAdmin(admin.ModelAdmin):
    list_display = ("application", "auth_profile", "start", "end")
    list_filter = ("application", "auth_profile", "start", "end")
    search_fields = (
        "application__application",
        "auth_profile__name",
        "auth_profile__uuid",
    )


@admin.register(ApplicationToken)
class ApplicationTokenAuthAdmin(NestedModelAdminMixin, admin.ModelAdmin):
    list_display = (
        "token",
        "contact_person",
        "organization",
        "administration",
        "application",
    )
    readonly_fields = ("token",)
    inlines = [ApplicationTokenAuthorizationInline]
    date_hierarchy = "created"
    extra = 0
