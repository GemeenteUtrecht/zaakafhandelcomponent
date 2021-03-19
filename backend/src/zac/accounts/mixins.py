from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied


# Deprecated
# this class is used only to support legacy SSR views
# All DRF views should use zac.api.permissions.DefinitionBasePermission and its subclasses
class PermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    def check_object_permissions(self, obj):
        user = self.request.user
        perms_required = self.get_permission_required()
        if not user.has_perms(perms_required, obj=obj):
            raise PermissionDenied(self.get_permission_denied_message())
