from django_filters import rest_framework as filters

from ..models import Activity


class ActivityFilter(filters.FilterSet):
    class Meta:
        model = Activity
        fields = ("zaak", "status")

    def filter_queryset(self, queryset):
        # for permission reasons, don't allow data retrieval without 'zaak' filter
        zaak = self.form.cleaned_data.get("zaak")
        if not zaak:
            return queryset.none()
        return super().filter_queryset(queryset)
