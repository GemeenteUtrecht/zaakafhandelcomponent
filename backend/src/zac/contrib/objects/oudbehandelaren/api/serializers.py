from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.accounts.api.serializers import UserSerializer
from zac.tests.compat import APIModelSerializer

from ..data import Oudbehandelaar, Oudbehandelaren


class OudbehandelaarSerializer(APIModelSerializer):
    email = serializers.EmailField(
        help_text=_("Email address related to `oudbehandelaar`.")
    )
    user = UserSerializer(
        help_text=_("User data of `oudbehandelaar`."),
    )
    changer = UserSerializer(
        help_text=_("User data of user that created `oudbehandelaar`."), allow_null=True
    )

    class Meta:
        model = Oudbehandelaar
        fields = ("email", "ended", "started", "user", "changer")
        extra_kwargs = {
            "ended": {"help_text": _("Datetime at which ROL ended.")},
            "started": {
                "help_text": _("Datetime ROL started. `registratiedatum` of ROL.")
            },
        }


class OudbehandelarenSerializer(APIModelSerializer):
    oudbehandelaren = OudbehandelaarSerializer(
        many=True, help_text=_("Array of `oudbehandelaren`.")
    )

    class Meta:
        model = Oudbehandelaren
        fields = ("zaak", "oudbehandelaren")
        extra_kwargs = {
            "zaak": {"help_text": _("URL-reference to ZAAK.")},
        }
