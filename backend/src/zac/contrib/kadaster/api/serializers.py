from django.utils.translation import gettext as _

from rest_framework import serializers


class SpellSuggestionsSerializer(serializers.Serializer):
    search_term = serializers.CharField(
        help_text=_("Potentially misspelled search term.")
    )
    num_found = serializers.IntegerField(
        help_text=_("Number of results found."),
    )
    start_offset = serializers.IntegerField(
        help_text=_(
            "Index of the first result. Used for pagination - not currently implemented."
        ),
    )
    end_offset = serializers.IntegerField(
        help_text=_(
            "Index of last result. Used for pagination - not currently implemented."
        )
    )
    suggestion = serializers.ListField(
        help_text=_("Alternative suggestions for search term."),
        child=serializers.CharField(),
    )


class SpellCheckSerializer(serializers.Serializer):
    suggestions = SpellSuggestionsSerializer(
        help_text=_("Potentially misspelled searches and spelling suggestions."),
        many=True,
    )

    def to_representation(self, instance):
        search_terms = instance["suggestions"][::2]
        suggestions = instance["suggestions"][1::2]
        instance["suggestions"] = [
            {"search_term": search_term, **suggestion}
            for search_term, suggestion in zip(search_terms, suggestions)
        ]
        return super().to_representation(instance)


class SuggestResultSerializer(serializers.Serializer):
    type = serializers.CharField(help_text=_("BAG types such as addresses or cities."))
    weergavenaam = serializers.CharField(
        help_text=_("Human readable name of BAG object.")
    )
    id = serializers.CharField(
        help_text=_("ID of BAG object. Can be used in lookup service.")
    )
    score = serializers.FloatField(
        help_text=_(
            "Score of BAG object related to search. A higher score means a better result."
        )
    )


class BagLocationSerializer(serializers.Serializer):
    num_found = serializers.IntegerField(
        help_text=_("Number of BAG objects found."), default=0
    )
    start = serializers.IntegerField(
        help_text=_(
            "Index of first result. Used for pagination - not currently implemented."
        ),
        default=0,
    )
    max_score = serializers.FloatField(
        help_text=_("Highest score of all the results found."), default=0
    )
    docs = SuggestResultSerializer(
        help_text=_("Suggestions made by the suggest service."),
        many=True,
        required=False,
    )
    spellcheck = SpellCheckSerializer(
        help_text=_("Spelling suggestions in case a spelling error is suspected."),
        required=False,
    )


class AddressSerializer(serializers.Serializer):
    straatnaam = serializers.CharField(help_text=_("Street name of BAG object."))
    nummer = serializers.CharField(help_text=_("Number of BAG object on street."))
    gemeentenaam = serializers.CharField(
        help_text=_("Name of municipality of BAG object.")
    )
    postcode = serializers.CharField(
        help_text=_("Postcode of BAG object."), required=False
    )
    provincienaam = serializers.CharField(help_text=_("Provice of BAG object."))


class BaseBagDataSerializer(serializers.Serializer):
    url = serializers.URLField(help_text=_("URL-reference to BAG object."))
    geometrie = serializers.JSONField(help_text=_("GeoJSON of BAG object geometry."))
    status = serializers.CharField(help_text=_("Status code of BAG object."))


class PandBagDataSerializer(BaseBagDataSerializer):
    oorspronkelijk_bouwjaar = serializers.IntegerField(
        help_text=_("The year the BAG object is built.")
    )


class VerblijfsobjectDataSerializer(BaseBagDataSerializer):
    oppervlakte = serializers.IntegerField(
        help_text=_("The surface area of the BAG object.")
    )


class PandSerializer(serializers.Serializer):
    adres = AddressSerializer(help_text=_("Address of pand."))
    bag_object = PandBagDataSerializer(help_text=_("Meta data of BAG object."))


class VerblijfsobjectSerializer(serializers.Serializer):
    adres = AddressSerializer(help_text=_("Address of verblijfsobject."))
    bag_object = VerblijfsobjectDataSerializer(help_text=_("Meta data of BAG object."))
