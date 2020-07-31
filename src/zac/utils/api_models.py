import json

from django.core.serializers.json import DjangoJSONEncoder

from dateutil.relativedelta import relativedelta
from relativedeltafield import format_relativedelta
from zgw_consumers.api_models.base import Model


def convert_model_to_json(value):
    if isinstance(value, list):
        return [convert_model_to_json(v) for v in value]

    if isinstance(value, dict):
        return {k: convert_model_to_json(v) for k, v in value.items()}

    if isinstance(value, Model):
        return {
            k: convert_model_to_json(v)
            for k, v in value.__dict__.items()
            if not k.startswith("_")
        }

    if isinstance(value, relativedelta):
        return format_relativedelta(value)

    try:
        json.dumps(value, cls=DjangoJSONEncoder)
    except TypeError:
        raise NotImplemented(f"{value} can't be converted to json")
    else:
        return value
