from typing import Optional

from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from rest_framework.serializers import ValidationError


class minLengthValidator:
    requires_context = True
    message = _(
        "A ZAAKEIGENSCHAP with `name`: {eigenschap} requires a minimum length of {min_length}."
    )

    def __init__(self, min_length: int = 0, eigenschap: Optional[str] = None):
        self.min_length = min_length
        self.eigenschap = eigenschap

    def __call__(self, value, serializer_field):
        if len(force_str(value)) < self.min_length:
            raise ValidationError(
                self.message.format(
                    eigenschap=self.eigenschap, min_length=self.min_length
                )
            )


class maxLengthValidator:
    requires_context = True
    message = _(
        "A ZAAKEIGENSCHAP with `name`: {eigenschap} requires a maximum length of {max_length}."
    )

    def __init__(self, max_length: int = 255, eigenschap: Optional[str] = None):
        self.max_length = max_length
        self.eigenschap = eigenschap

    def __call__(self, value, serializer_field):
        if len(force_str(value)) > self.max_length:
            raise ValidationError(
                self.message.format(
                    eigenschap=self.eigenschap, max_length=self.max_length
                )
            )
