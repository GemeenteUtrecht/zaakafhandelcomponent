from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from zac.elasticsearch.drf_api.serializers import ZaakDocumentSerializer
from zac.utils.validators import ImmutableFieldValidator

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
    board = BoardSerializer(
        source="column.board", read_only=True, help_text=_("Board of the item")
    )
    column_uuid = serializers.SlugRelatedField(
        queryset=BoardColumn.objects.all(),
        source="column",
        slug_field="uuid",
        write_only=True,
        help_text=_("UUID4 of the board column"),
    )
    column = BoardColumnSerializer(help_text=_("Column of the board"), read_only=True)
    zaak = ZaakDocumentSerializer(
        source="zaak_document", read_only=True, help_text=_("Details of the zaak")
    )

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
            "zaak",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "object": {"validators": [ImmutableFieldValidator()]},
        }

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)

        object = validated_attrs.get("object")
        column = validated_attrs.get("column")

        if (
            not self.instance
            and BoardItem.objects.filter(
                object=object, column__board=column.board
            ).exists()
        ):
            raise serializers.ValidationError(_("This object is already on the board"))

        return validated_attrs

    def validate_column_uuid(self, value):
        if self.instance and value.board != self.instance.column.board:
            raise serializers.ValidationError(
                _("The board of the item can't be changed")
            )

        return value
