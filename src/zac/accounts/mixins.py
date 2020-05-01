from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class PermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    pass
