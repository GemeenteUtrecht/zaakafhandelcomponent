from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.elasticsearch.data import FlattenedNestedAggregation, ParentAggregation
from zac.elasticsearch.drf_api.fields import OrderedMultipleChoiceField
from zac.elasticsearch.drf_api.serializers import (
    DEFAULT_ES_ZAAKDOCUMENT_FIELDS,
    SearchZaaktypeSerializer,
    ZaakDocumentSerializer,
)
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
        source="zaak_document", read_only=True, help_text=_("Details of the ZAAK")
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
            raise serializers.ValidationError(_("This OBJECT is already on the board"))

        return validated_attrs

    def validate_column_uuid(self, value):
        if self.instance and value.board != self.instance.column.board:
            raise serializers.ValidationError(
                _("The board of the item can't be changed")
            )

        return value


class ManagementDashboardSerializer(serializers.Serializer):
    zaaktype = SearchZaaktypeSerializer(
        required=False, help_text=_("Properties to identify ZAAKTYPEs.")
    )
    fields = OrderedMultipleChoiceField(
        default=[
            "identificatie",
            "bronorganisatie",
            "omschrijving",
            "status",
            "startdatum",
            "deadline",
            "vertrouwelijkheidaanduiding",
            "zaaktype",
        ],
        help_text=_(
            "Fields that will be returned with the search results. Will always include `identificatie` and `bronorganisatie`."
        ),
        choices=DEFAULT_ES_ZAAKDOCUMENT_FIELDS,
    )

    def validate_fields(self, fields):
        if isinstance(fields, set):
            fields.add("identificatie")
            fields.add("bronorganisatie")
            fields = list(fields)
        return sorted(fields)


class FlattenedNestedAggregationSerializer(APIModelSerializer):
    zaaktype_omschrijving = serializers.SerializerMethodField(
        help_text=_("Description of ZAAKTYPE.")
    )
    zaaktype_catalogus = serializers.CharField(
        help_text=_("URL-reference of catalogus related to ZAAKTYPE."),
        source="parent_key",
    )
    zaaktype_identificatie = serializers.CharField(
        help_text=_("Identificatie of ZAAKTYPE."), source="child_key"
    )
    count = serializers.IntegerField(
        help_text=_("Number of active ZAAKs per ZAAKTYPE."), source="doc_count"
    )

    class Meta:
        model = FlattenedNestedAggregation
        fields = (
            "zaaktype_omschrijving",
            "zaaktype_catalogus",
            "count",
            "zaaktype_identificatie",
        )

    def get_zaaktype_omschrijving(self, obj) -> str:
        return self.context["zaaktypen"].get(obj.parent_key, {}).get(obj.child_key, "")


class SummaryManagementDashboardSerializer(APIModelSerializer):
    catalogus = serializers.CharField(
        help_text=_("URL-reference of CATALOGUS related to ZAAKTYPE."), source="key"
    )
    zaaktypen = FlattenedNestedAggregationSerializer(
        help_text=_("Summary of ZAAKs of ZAAKTYPEs per CATALOGUS."),
        many=True,
        source="flattened_child_buckets",
    )
    count = serializers.IntegerField(
        help_text=_("Number of active ZAAKs per CATALOGUS."), source="doc_count"
    )

    class Meta:
        model = ParentAggregation
        fields = ("catalogus", "zaaktypen", "count")

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["zaaktypen"] = list(
            sorted(ret["zaaktypen"], key=lambda zt: zt["zaaktype_omschrijving"])
        )
        return ret
