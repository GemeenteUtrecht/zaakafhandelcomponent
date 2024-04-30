from django.conf import settings
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.core.services import get_zaak

from .constants import IndexTypes


class ReindexZaakSerializer(serializers.Serializer):
    chunk_size = serializers.IntegerField(
        default=settings.CHUNK_SIZE,
        help_text=_(
            "Number of ZAAKen to be iterated through per bulk update action. Be careful with this setting. Defaults to {chunk_size}."
        ).format(chunk_size=settings.CHUNK_SIZE),
    )
    max_workers = serializers.IntegerField(
        default=settings.MAX_WORKERS,
        help_text=_(
            "Number of parallel workers used to fetch data from relevant APIs. Be careful with this setting. Defaults to {workers}."
        ).format(workers=settings.MAX_WORKERS),
    )


class ManageIndexSerializer(ReindexZaakSerializer):
    index = serializers.ChoiceField(
        choices=IndexTypes.choices, default=IndexTypes.index_all
    )
    reset_indices = serializers.BooleanField(
        default=False,
        help_text=_(
            "On `True` wipes the current indices and reindexes everything. Defaults to `False` to make sure the index isn't accidentally wiped."
        ),
    )
    reindex_last = serializers.IntegerField(
        help_text=_(
            "The number of ZAAKen to be indexed sorted by latest ZAAK.identificatie."
        ),
        required=False,
    )
    reindex_zaak = serializers.URLField(
        help_text=_("URL-reference to ZAAK to be reindexed."),
        required=False,
    )

    def validate_reindex_zaak(self, url):
        try:
            zaak = get_zaak(zaak_url=url)
        except Exception as exc:
            raise serializers.ValidationError(detail=exc.args[0])
        return zaak

    def validate(self, data):
        validated_data = super().validate(data)
        if validated_data["reset_indices"]:
            # Call index_all with other attributes if given.
            # Remove other arguments if given.
            validated_data.pop("reindex_last", None)
            validated_data.pop("reindex_zaak", None)
            return validated_data

        reindex = [
            bool(validated_data.get("reindex_last")),
            bool(validated_data.get("reindex_zaak")),
        ]
        if (not any(reindex)) or all(reindex):
            raise serializers.ValidationError(
                _("Set one of `reindex_last`, `reindex_zaak` or `reset_indices`.")
            )

        return validated_data
