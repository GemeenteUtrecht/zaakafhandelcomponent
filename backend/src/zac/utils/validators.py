from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError


class ImmutableFieldValidator:
    """
    Validate if a field has changed.
    """

    requires_context = True
    message = _("This field can't be changed.")

    def __call__(self, new_value, serializer_field):
        field_name = serializer_field.source_attrs[-1]
        instance = getattr(serializer_field.parent, "instance", None)
        if instance:
            old_value = getattr(instance, field_name)
            if old_value != new_value:
                raise ValidationError(self.message)
