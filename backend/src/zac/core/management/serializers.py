from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from rest_framework.serializers import (
    CharField,
    IntegerField,
    Serializer,
    ValidationError,
)

from zac.core.cache import is_redis_cache


class CacheResetSerializer(Serializer):
    key = CharField(
        help_text=_("Key to be cleared from cache."),
        required=False,
    )
    pattern = CharField(
        help_text=_(
            "Pattern to be cleared from cache. Only allowed for redis cache. `*` clears all cache keys."
        ),
        required=False,
    )
    count = IntegerField(
        help_text=_("Number of cleared cached keys."), allow_null=True, read_only=True
    )

    def validate(self, data):
        validated_data = super().validate(data)
        key_in_data = "key" in validated_data
        pattern_in_data = "pattern" in validated_data

        if pattern_in_data and not is_redis_cache():
            raise ValidationError(
                _("Pattern is not allowed for non-redis caches. Please provide a key.")
            )

        if not pattern_in_data and not key_in_data:
            raise ValidationError(_("Please provide either a key or a pattern."))

        return validated_data

    def perform(self) -> int:
        assert hasattr(
            self, "validated_data"
        ), "Serializer must be validated before perform is called."

        mapping = {
            "key": [cache.delete, self.validated_data.get("key", False)],
        }
        if is_redis_cache():
            mapping["pattern"] = [
                cache.delete_pattern,
                self.validated_data.get("pattern", False),
            ]

        count = 0
        for key, [func, arg] in mapping.items():
            if arg:
                count += int(func(arg))

        self.validated_data["count"] = count
