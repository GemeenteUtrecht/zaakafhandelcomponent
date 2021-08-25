from django_filters import rest_framework as filters

from ..models import BoardItem


class BoardItemFilter(filters.FilterSet):
    class Meta:
        model = BoardItem
        fields = ("board__uuid", "board__slug")

    @classmethod
    def filter_for_field(cls, f, name, lookup_expr):
        """add help texts from the model"""
        filter = super().filter_for_field(f, name, lookup_expr)
        filter.extra["help_text"] = f.help_text
        return filter
