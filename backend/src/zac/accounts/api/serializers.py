from datetime import date

from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from ..constants import AccessRequestResult
from ..models import AccessRequest, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "is_staff",
            "email",
        )


class CatalogusURLSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=1000, required=True)


class ZaakAccessSerializer(serializers.ModelSerializer):
    requester = serializers.SlugRelatedField(
        slug_field="username", queryset=User.objects.all()
    )
    handler = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = AccessRequest
        fields = (
            "requester",
            "handler",
            "zaak",
            "comment",
            "result",
            "start_date",
            "end_date",
        )
        extra_kwargs = {"result": {"read_only": True}}

    def validate(self, data):
        valid_data = super().validate(data)

        requester = valid_data["requester"]
        zaak_url = valid_data["zaak"]

        if (
            requester.initiated_requests.filter(
                zaak=zaak_url, result=AccessRequestResult.approve
            )
            .actual()
            .exists()
        ):
            raise serializers.ValidationError(
                _("User %(requester)s already has an access to zaak %(zaak)s")
                % {"requester": requester.username, "zaak": zaak_url}
            )

        return valid_data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        start_date = date.today()

        validated_data.update(
            {
                "handler": request.user,
                "result": AccessRequestResult.approve,
                "start_date": start_date,
            }
        )

        access_request = super().create(validated_data)

        # close pending access requests
        pending_requests = access_request.requester.initiated_requests.filter(
            zaak=access_request.zaak, result=""
        ).actual()
        if pending_requests.exists():
            pending_requests.update(
                result=AccessRequestResult.approve,
                start_date=start_date,
                end_date=access_request.end_date,
                comment=f"Automatically approved after access request #{access_request.id}",
            )

        return access_request
