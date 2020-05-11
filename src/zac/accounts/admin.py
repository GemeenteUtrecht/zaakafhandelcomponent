from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import AuthorizationProfile, PermissionSet, User, UserAuthorizationProfile


class UserAuthorizationProfileInline(admin.TabularInline):
    model = UserAuthorizationProfile
    extra = 1


@admin.register(User)
class _UserAdmin(UserAdmin):
    inlines = [UserAuthorizationProfileInline]


@admin.register(PermissionSet)
class PermissionSetAdmin(admin.ModelAdmin):
    list_display = ("name", "permissions", "zaaktype_identificaties", "max_va")
    list_filter = ("max_va",)
    search_fields = ("name",)


@admin.register(AuthorizationProfile)
class AuthorizationProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "display_permission_sets")
    list_filter = ("permission_sets",)
    search_fields = ("name", "uuid")
    filter_horizontal = ("permission_sets",)

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
    search_fields = ("user__usernamae", "auth_profile__name", "auth_profile__uuid")
