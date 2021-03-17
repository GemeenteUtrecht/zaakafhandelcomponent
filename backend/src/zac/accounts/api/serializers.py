from datetime import date, datetime

from django.db import transaction
from django.utils.timezone import make_aware
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from zac.core.permissions import zaken_inzien

from ..constants import AccessRequestResult, PermissionObjectType
from ..email import send_email_to_requester
from ..models import AccessRequest, PermissionDefinition, User


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
        slug_field="username",
        queryset=User.objects.all(),
        help_text=_("Username of access requester/grantee"),
    )
    handler = serializers.SlugRelatedField(
        slug_field="username",
        read_only=True,
        help_text=_("Username of access handler/granter"),
    )

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
            PermissionDefinition.objects.for_user(requester)
            .filter(object_url=zaak_url, permission=zaken_inzien.name)
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
        start_date = validated_data.get("start_date", date.today())

        validated_data.update(
            {
                "handler": request.user,
                "result": AccessRequestResult.approve,
                "start_date": start_date,
            }
        )

        access_request = super().create(validated_data)

        # TODO refactor relations between access request and permission definitions
        # add permission definition
        permission_definition = PermissionDefinition.objects.create(
            object_url=access_request.zaak,
            object_type=PermissionObjectType.zaak,
            permission=zaken_inzien.name,
            start_date=make_aware(
                datetime.combine(access_request.start_date, datetime.min.time())
            ),
            end_date=make_aware(
                datetime.combine(access_request.end_date, datetime.min.time())
            )
            if access_request.end_date
            else None,
        )
        access_request.requester.permission_definitions.add(permission_definition)

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

        # send email
        transaction.on_commit(
            lambda: send_email_to_requester(access_request, request, ui=True)
        )
        return access_request
