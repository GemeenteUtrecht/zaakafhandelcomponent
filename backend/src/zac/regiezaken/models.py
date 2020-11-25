from django.contrib.postgres.fields import ArrayField


class ZaakTypeArrayField(ArrayField):
    system_check_removed_details = {
        "msg": (
            "ZaakTypeArrayField has been removed except for support in "
            "historical migrations."
        ),
        "id": "fields.75152992",
    }
