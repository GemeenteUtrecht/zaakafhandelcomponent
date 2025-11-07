from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters

from ..models import BoardItem


class BoardItemFilter(filters.FilterSet):
    board_uuid = filters.UUIDFilter(
        field_name="column__board__uuid", help_text=_("UUID of the board")
    )
    board_slug = filters.CharFilter(
        field_name="column__board__slug", help_text=_("Slug of the board")
    )
    zaak_url = filters.CharFilter(
        field_name="object", help_text=_("URL-reference of the ZAAK")
    )
    object = filters.CharFilter(
        field_name="object", help_text=_("URL-reference of the OBJECT")
    )

    class Meta:
        model = BoardItem
        fields = ("board_uuid", "board_slug", "zaak_url", "object")
