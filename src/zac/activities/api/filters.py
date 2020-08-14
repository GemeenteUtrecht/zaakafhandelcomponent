from django_filters import rest_framework as filters
from rest_framework import exceptions

from zac.core.services import get_zaak

from ..models import Activity


class ActivityFilter(filters.FilterSet):
    class Meta:
        model = Activity
        fields = ("zaak", "status")

    def filter_queryset(self, queryset):
        # for permission reasons, don't allow data retrieval without 'zaak' filter
        zaak_url = self.form.cleaned_data.get("zaak")
        if not zaak_url:
            return queryset.none()

        # permission check on the zaak itself
        zaak = get_zaak(zaak_url=zaak_url)
        if not self.request.user.has_perm("activities:read", zaak):
            raise exceptions.PermissionDenied(
                "Not allowed to read activities for this zaak."
            )

        return super().filter_queryset(queryset)
