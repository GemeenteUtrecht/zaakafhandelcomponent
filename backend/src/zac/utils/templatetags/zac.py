from decimal import Decimal
from typing import Any

from django.template import Library

from dateutil.parser import parse as dateutil_parse

register = Library()


@register.filter
def parse(value: Any):
    if isinstance(value, (int, float, Decimal)):
        return value

    try:
        date_like = dateutil_parse(value)
    except ValueError:
        pass
    else:
        if date_like:
            return date_like

    return value
