import json

from django.core.serializers.json import DjangoJSONEncoder

from dateutil.relativedelta import relativedelta
from relativedeltafield import format_relativedelta
from zgw_consumers.api_models.base import Model


def serialize(value):
    if isinstance(value, list):
        return [serialize(v) for v in value]

    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}

    if isinstance(value, Model):
        return {
            k: serialize(v) for k, v in value.__dict__.items() if not k.startswith("_")
        }

    if isinstance(value, relativedelta):
        return format_relativedelta(value)

    try:
        json.dumps(value, cls=DjangoJSONEncoder)
    except TypeError:
        raise NotImplementedError(f"{value} can't be converted to json")
    else:
        return value
