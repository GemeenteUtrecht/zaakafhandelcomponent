from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from ..models import Board, BoardColumn, BoardItem


class BoardColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardColumn
        fields = ("uuid", "name", "slug", "order", "created", "modified")


class BoardSerializer(serializers.HyperlinkedModelSerializer):
    columns = BoardColumnSerializer(many=True, help_text=_("Columns of the board"))

    class Meta:
        model = Board
        fields = ("url", "uuid", "name", "slug", "created", "modified", "columns")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
        }


class BoardItemSerializer(serializers.HyperlinkedModelSerializer):
    column_uuid = serializers.SlugRelatedField(
        queryset=BoardColumn.objects.all(),
        source="column",
        slug_field="uuid",
        write_only=True,
        help_text=_("UUID4 of the board column"),
    )
    column = BoardColumnSerializer(help_text=_("Column of the board"), read_only=True)

    class Meta:
        model = BoardItem
        fields = (
            "url",
            "uuid",
            "object_type",
            "object",
            "board",
            "column",
            "column_uuid",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "board": {
                "lookup_field": "uuid",
                "read_only": True,
            },
        }
