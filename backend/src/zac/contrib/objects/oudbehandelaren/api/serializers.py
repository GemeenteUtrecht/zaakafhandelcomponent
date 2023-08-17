from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.api.serializers import UserSerializer

from ..data import Oudbehandelaren


class OudbehandelarenSerializer(APIModelSerializer):
    email = serializers.EmailField(
        help_text=_("Email address related to `oudbehandelaar`.")
    )
    user = UserSerializer(
        help_text=_("User data of `oudbehandelaar`."),
    )

    class Meta:
        model = Oudbehandelaren
        fields = (
            "email",
            "ended",
            "started",
            "user",
        )
        extra_kwargs = {
            "ended": {"help_text": _("Datetime at which ROL ended.")},
            "started": {
                "help_text": _("Datetime ROL started. `registratiedatum` of ROL.")
            },
        }
