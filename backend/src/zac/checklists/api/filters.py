from django_filters import rest_framework as filters

from ..models import Checklist


class ChecklistFilter(filters.FilterSet):
    class Meta:
        model = Checklist
        fields = ("zaak",)
