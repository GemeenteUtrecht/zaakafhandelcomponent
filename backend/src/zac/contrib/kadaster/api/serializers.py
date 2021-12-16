from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.api_models.base import factory
from zgw_consumers.drf.serializers import APIModelSerializer

from .data import (
    Address,
    BagLocation,
    BagResponse,
    BaseBagData,
    Pand,
    PandBagData,
    SpellCheck,
    SpellSuggestions,
    SuggestResult,
    Verblijfsobject,
    VerblijfsobjectBagData,
)


class SpellSuggestionsSerializer(APIModelSerializer):
    suggestion = serializers.ListField(
        help_text=_("Alternative suggestions for search term."),
        child=serializers.CharField(),
    )

    class Meta:
        model = SpellSuggestions
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


class SpellCheckSerializer(APIModelSerializer):
    suggestions = SpellSuggestionsSerializer(
        help_text=_("Potentially misspelled searches and spelling suggestions."),
        many=True,
    )

    class Meta:
        model = SpellCheck
        fields = ("suggestions",)


class SuggestResultSerializer(APIModelSerializer):
    class Meta:
        model = SuggestResult
        fields = (
            "type",
            "weergavenaam",
            "id",
            "score",
        )
        extra_kwargs = {
            "type": {"help_text": _("BAG types such as addresses or cities.")},
            "weergavenaam": {"help_text": _("Human readable name of BAG object.")},
            "id": {"help_text": _("ID of BAG object. Can be used in lookup service.")},
            "score": {
                "help_text": _(
                    "Score of BAG object related to search. A higher score means a better result."
                )
            },
        }


class BagLocationSerializer(APIModelSerializer):
    docs = SuggestResultSerializer(
        help_text=_("Suggestions made by the suggest service."),
        many=True,
        required=False,
    )

    class Meta:
        model = BagLocation
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


class BagResponseSerializer(APIModelSerializer):
    response = BagLocationSerializer(
        required=False,
    )
    spellcheck = SpellCheckSerializer(
        help_text=_("Spelling suggestions in case a spelling error is suspected."),
        required=False,
    )

    class Meta:
        model = BagResponse
        fields = (
            "response",
            "spellcheck",
        )


class AddressSerializer(APIModelSerializer):
    class Meta:
        model = Address
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


class BaseBagDataSerializer(APIModelSerializer):
    geometrie = serializers.JSONField(help_text=_("GeoJSON of BAG object geometry."))

    class Meta:
        model = BaseBagData
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
        model = PandBagData
        fields = BaseBagDataSerializer.Meta.fields + ["oorspronkelijk_bouwjaar"]
        extra_kwargs = {
            **BaseBagDataSerializer.Meta.extra_kwargs,
            "oorspronkelijk_bouwjaar": {
                "help_text": _("The year the BAG object is built."),
            },
        }


class VerblijfsobjectDataSerializer(BaseBagDataSerializer):
    class Meta(BaseBagDataSerializer.Meta):
        model = VerblijfsobjectBagData
        fields = BaseBagDataSerializer.Meta.fields + ["oppervlakte"]
        extra_kwargs = {
            **BaseBagDataSerializer.Meta.extra_kwargs,
            "oppervlakte": {
                "help_text": _("The surface area of the BAG object."),
            },
        }


class PandSerializer(APIModelSerializer):
    adres = AddressSerializer(help_text=_("Address of pand."))
    bag_object = PandBagDataSerializer(help_text=_("Meta data of BAG object."))

    class Meta:
        model = Pand
        fields = (
            "adres",
            "bag_object",
        )


class VerblijfsobjectSerializer(APIModelSerializer):
    adres = AddressSerializer(help_text=_("Address of verblijfsobject."))
    bag_object = VerblijfsobjectDataSerializer(help_text=_("Meta data of BAG object."))

    class Meta:
        model = Verblijfsobject
        fields = (
            "adres",
            "bag_object",
        )
