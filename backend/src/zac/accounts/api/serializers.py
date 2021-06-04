from datetime import date, datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.timezone import make_aware
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from zac.core.permissions import zaken_inzien

from ..constants import AccessRequestResult, PermissionObjectType
from ..email import send_email_to_requester
from ..models import AccessRequest, AtomicPermission, User, UserAtomicPermission


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name")

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "full_name",
            "last_name",
            "is_staff",
            "email",
        )


class CatalogusURLSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=1000, required=True)


class UsernameField(serializers.SlugRelatedField):
    def get_attribute(self, instance):
        """
        Since it's M2M field it requires some tweaking
        """
        try:
            if isinstance(instance, dict):
                instance = instance["requester"]
            else:
                instance = instance.users.get()
        except ObjectDoesNotExist:
            return None

        except (KeyError, AttributeError) as exc:
            msg = (
                "Got {exc_type} when attempting to get a value for field "
                "`{field}` on serializer `{serializer}`.\nThe serializer "
                "field might be named incorrectly and not match "
                "any attribute or key on the `{instance}` instance.\n"
                "Original exception text was: {exc}.".format(
                    exc_type=type(exc).__name__,
                    field=self.field_name,
                    serializer=self.parent.__class__.__name__,
                    instance=instance.__class__.__name__,
                    exc=exc,
                )
            )
            raise type(exc)(msg)

        return instance


class GrantPermissionSerializer(serializers.ModelSerializer):
    requester = UsernameField(
        slug_field="username",
        queryset=User.objects.all(),
        help_text=_("User to give the permission to"),
    )
    comment = serializers.CharField(
        required=False, help_text=_("Comment provided by the granter of the permission")
    )

    class Meta:
        model = AtomicPermission
        fields = (
            "requester",
            "permission",
            "zaak",
            "comment",
            "start_date",
            "end_date",
        )
        extra_kwargs = {
            "permission": {"default": zaken_inzien.name},
            "zaak": {"source": "object_url"},
        }

    def validate(self, data):
        valid_data = super().validate(data)

        requester = valid_data["requester"]
        object_url = valid_data["object_url"]
        permission = valid_data["permission"]

        if (
            AtomicPermission.objects.for_user(requester)
            .filter(object_url=object_url, permission=permission)
            .actual()
            .exists()
        ):
            raise serializers.ValidationError(
                _("User %(requester)s already has an access to zaak %(zaak)s")
                % {"requester": requester.username, "zaak": object_url}
            )

        return valid_data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        validated_data.update({"object_type": PermissionObjectType.zaak})
        user = validated_data.pop("requester")
        comment = validated_data.pop("comment")

        atomic_permission = super().create(validated_data)
        user_atomic_permission = UserAtomicPermission.objects.create(
            user=user, atomic_permission=atomic_permission, comment=comment
        )
        # close pending access requests
        pending_requests = user.initiated_requests.filter(
            zaak=validated_data["object_url"], result=""
        ).actual()
        if pending_requests.exists():
            pending_requests.update(
                result=AccessRequestResult.approve,
                user_atomic_permission=user_atomic_permission,
            )

        # send email
        transaction.on_commit(
            lambda: send_email_to_requester(
                user,
                zaak_url=validated_data["object_url"],
                result=AccessRequestResult.approve,
                request=request,
                ui=True,
            )
        )
        return atomic_permission


class AccessRequestDetailSerializer(serializers.HyperlinkedModelSerializer):
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
            "url",
            "requester",
            "handler",
            "zaak",
            "comment",
            "result",
            "requested_date",
            "handled_date",
        )


class CreateAccessRequestSerializer(serializers.HyperlinkedModelSerializer):
    requester = serializers.SlugRelatedField(
        slug_field="username",
        read_only=True,
        help_text=_("Username of access requester/grantee"),
    )

    class Meta:
        model = AccessRequest
        fields = ("url", "zaak", "comment", "requester")

    def validate(self, data):
        valid_data = super().validate(data)

        request = self.context["request"]
        requester = request.user
        zaak_url = valid_data["zaak"]

        if (
            AtomicPermission.objects.for_user(requester)
            .filter(object_url=zaak_url, permission=zaken_inzien.name)
            .actual()
            .exists()
        ):
            raise serializers.ValidationError(
                _("User %(requester)s already has an access to zaak %(zaak)s")
                % {"requester": requester.username, "zaak": zaak_url}
            )

        if (
            requester.initiated_requests.filter(zaak=zaak_url, result="")
            .actual()
            .exists()
        ):
            raise serializers.ValidationError(
                _(
                    "User %(requester)s already has an pending access request to zaak %(zaak)s"
                )
                % {"requester": requester.username, "zaak": zaak_url}
            )

        valid_data["requester"] = requester
        return valid_data


class HandleAccessRequestSerializer(serializers.HyperlinkedModelSerializer):
    requester = serializers.SlugRelatedField(
        slug_field="username",
        read_only=True,
        help_text=_("Username of access requester/grantee"),
    )
    handler = serializers.SlugRelatedField(
        slug_field="username",
        read_only=True,
        help_text=_("Username of access handler/granter"),
    )
    handler_comment = serializers.CharField(
        required=False, help_text=_("Comment of the handler+")
    )
    start_date = serializers.DateField(
        default=date.today, help_text=_("Start date of the access")
    )
    end_date = serializers.DateField(
        required=False, help_text=_("End date of the access")
    )

    class Meta:
        model = AccessRequest
        fields = (
            "url",
            "requester",
            "handler",
            "result",
            "handler_comment",
            "start_date",
            "end_date",
        )
        extra_kwargs = {"url": {"read_only": True}, "result": {"allow_blank": False}}

    def validate(self, data):
        valid_data = super().validate(data)

        if self.instance.result:
            raise serializers.ValidationError(
                _("This access request has already been handled")
            )

        request = self.context["request"]

        valid_data["handler"] = request.user
        valid_data["handled_date"] = date.today()

        return valid_data

    @transaction.atomic
    def update(self, instance, validated_data):
        handler_comment = validated_data.pop("handler_comment")
        start_date = validated_data.pop("start_date")
        end_date = validated_data.pop("end_date")

        access_request = super().update(instance, validated_data)

        if access_request.result == AccessRequestResult.approve:
            # add permission definition
            atomic_permission = AtomicPermission.objects.create(
                object_url=access_request.zaak,
                object_type=PermissionObjectType.zaak,
                permission=zaken_inzien.name,
                start_date=make_aware(
                    datetime.combine(start_date, datetime.min.time())
                ),
                end_date=make_aware(datetime.combine(end_date, datetime.min.time()))
                if end_date
                else None,
            )
            user_atomic_permission = UserAtomicPermission.objects.create(
                atomic_permission=atomic_permission,
                user=access_request.requester,
                comment=handler_comment,
            )
            access_request.user_atomic_permission = user_atomic_permission
            access_request.save()

        # send email
        request = self.context.get("request")
        transaction.on_commit(
            lambda: send_email_to_requester(
                access_request.requester,
                zaak_url=access_request.zaak,
                result=access_request.result,
                request=request,
                ui=True,
            )
        )
        return access_request
