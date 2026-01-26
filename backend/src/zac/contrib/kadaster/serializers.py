from django.conf import settings
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework_dataclasses.serializers import DataclassSerializer

from zac.api.proxy import ProxySerializer

from .data import (
    Address,
    AddressSearchResponse,
    BagLocation,
    BaseBagData,
    Pand,
    PandBagData,
    SpellCheck,
    SpellSuggestions,
    SuggestResult,
    Verblijfsobject,
    VerblijfsobjectBagData,
)


class SpellSuggestionsSerializer(DataclassSerializer):
    suggestion = serializers.ListField(
        help_text=_("Alternative suggestions for search term."),
        child=serializers.CharField(),
    )

    class Meta:
        dataclass = SpellSuggestions
        fields = (
            "search_term",
            "num_found",
            "start_offset",
            "end_offset",
            "suggestion",
        )
        extra_kwargs = {
            "search_term": {"help_text": _("Potentially misspelled search term.")},
            "num_found": {"help_text": _("Number of results found.")},
            "start_offset": {
                "help_text": _(
                    "Index of the first result. Used for pagination - not currently implemented."
                )
            },
            "end_offset": {
                "help_text": _(
                    "Index of last result. Used for pagination - not currently implemented."
                )
            },
        }


class SpellCheckSerializer(DataclassSerializer):
    suggestions = SpellSuggestionsSerializer(
        help_text=_("Potentially misspelled searches and spelling suggestions."),
        many=True,
    )

    class Meta:
        dataclass = SpellCheck
        fields = ("suggestions",)


class SuggestResultSerializer(DataclassSerializer):
    class Meta:
        dataclass = SuggestResult
        fields = (
            "type",
            "weergavenaam",
            "id",
            "score",
        )
        extra_kwargs = {
            "type": {"help_text": _("BAG types such as addresses or cities.")},
            "weergavenaam": {"help_text": _("Human readable name of BAG object.")},
            "id": {
                "help_text": _("`id` of BAG object. Can be used in lookup service.")
            },
            "score": {
                "help_text": _(
                    "Score of BAG object related to search. A higher score means a better result."
                )
            },
        }


class BagLocationSerializer(DataclassSerializer):
    docs = SuggestResultSerializer(
        help_text=_("Suggestions made by the suggest service."),
        many=True,
        required=False,
    )

    class Meta:
        dataclass = BagLocation
        fields = ("num_found", "start", "max_score", "docs")
        extra_kwargs = {
            "num_found": {"help_text": _("Number of BAG objects found.")},
            "start": {
                "help_text": _(
                    "Index of first result. Used for pagination - not currently implemented."
                )
            },
            "max_score": {"help_text": _("Highest score of all the results found.")},
        }


class AddressSearchResponseSerializer(DataclassSerializer):
    response = BagLocationSerializer(
        required=False,
    )
    spellcheck = SpellCheckSerializer(
        help_text=_("Spelling suggestions in case a spelling error is suspected."),
        required=False,
    )

    class Meta:
        dataclass = AddressSearchResponse
        fields = (
            "response",
            "spellcheck",
        )


class AddressSerializer(DataclassSerializer):
    class Meta:
        dataclass = Address
        fields = (
            "straatnaam",
            "nummer",
            "gemeentenaam",
            "postcode",
            "provincienaam",
        )
        extra_kwargs = {
            "straatnaam": {"help_text": _("Street name of BAG object.")},
            "nummer": {"help_text": _("Number of BAG object on street.")},
            "gemeentenaam": {"help_text": _("Name of municipality of BAG object.")},
            "postcode": {"help_text": _("Postcode of BAG object."), "required": False},
            "provincienaam": {
                "help_text": _("Province of BAG object."),
                "required": False,
            },
        }


class BaseBagDataSerializer(DataclassSerializer):
    geometrie = serializers.JSONField(help_text=_("GeoJSON of BAG object geometry."))

    class Meta:
        dataclass = BaseBagData
        fields = [
            "url",
            "geometrie",
            "status",
        ]
        extra_kwargs = {
            "url": {"help_text": _("URL-reference to BAG object.")},
            "status": {"help_text": _("Status code of BAG object.")},
        }


class PandBagDataSerializer(BaseBagDataSerializer):
    class Meta(BaseBagDataSerializer.Meta):
        dataclass = PandBagData
        fields = BaseBagDataSerializer.Meta.fields + ["oorspronkelijk_bouwjaar"]
        extra_kwargs = {
            **BaseBagDataSerializer.Meta.extra_kwargs,
            "oorspronkelijk_bouwjaar": {
                "help_text": _("The year the BAG object is built."),
            },
        }


class VerblijfsobjectDataSerializer(BaseBagDataSerializer):
    class Meta(BaseBagDataSerializer.Meta):
        dataclass = VerblijfsobjectBagData
        fields = BaseBagDataSerializer.Meta.fields + ["oppervlakte"]
        extra_kwargs = {
            **BaseBagDataSerializer.Meta.extra_kwargs,
            "oppervlakte": {
                "help_text": _("The surface area of the BAG object."),
            },
        }


class FindPandSerializer(DataclassSerializer):
    adres = AddressSerializer(help_text=_("Address of pand."))
    bag_object = PandBagDataSerializer(help_text=_("Meta data of BAG object."))

    class Meta:
        dataclass = Pand
        fields = (
            "adres",
            "bag_object",
        )


class VerblijfsobjectSerializer(DataclassSerializer):
    adres = AddressSerializer(help_text=_("Address of verblijfsobject."))
    bag_object = VerblijfsobjectDataSerializer(help_text=_("Meta data of BAG object."))

    class Meta:
        dataclass = Verblijfsobject
        fields = (
            "adres",
            "bag_object",
        )


class PandenSerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["BAG_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "paths",
        "/panden/{pandidentificatie}",
        "get",
        "responses",
        200,
        "content",
        "application/json",
        "schema",
    ]


class NummerAanduidingenSerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["BAG_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "paths",
        "/nummeraanduidingen/{nummeraanduidingidentificatie}",
        "get",
        "responses",
        200,
        "content",
        "application/json",
        "schema",
    ]
