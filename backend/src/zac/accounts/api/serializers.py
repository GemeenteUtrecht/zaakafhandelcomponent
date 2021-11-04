from datetime import date, datetime
from typing import List

from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.timezone import make_aware
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.concurrent import parallel
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.polymorphism import GroupPolymorphicSerializer
from zac.core.permissions import zaken_inzien
from zac.core.services import (
    find_zaak,
    get_informatieobjecttypen_for_zaaktype,
    get_zaak,
    get_zaaktypen,
)
from zgw.models.zrc import Zaak

from ..constants import (
    AccessRequestResult,
    PermissionObjectTypeChoices,
    PermissionReason,
)
from ..email import send_email_to_requester
from ..models import (
    AccessRequest,
    AtomicPermission,
    AuthorizationProfile,
    BlueprintPermission,
    Role,
    User,
    UserAtomicPermission,
)
from ..permissions import object_type_registry, registry


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name")
    groups = serializers.StringRelatedField(many=True)

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
            "groups",
        )


class GroupSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(
        help_text=_("Human readable name that identifies the group.")
    )

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "full_name",
        ]

    def get_full_name(self, obj) -> str:
        return _("Group") + ": " + obj.name


class ManageGroupSerializer(GroupSerializer):
    users = serializers.SlugRelatedField(
        source="user_set",
        many=True,
        read_only=False,
        slug_field="username",
        queryset=User.objects.all(),
        required=False,
    )

    class Meta(GroupSerializer.Meta):
        model = GroupSerializer.Meta.model
        fields = GroupSerializer.Meta.fields + ["users"]

    @transaction.atomic()
    def create(self, validated_data):
        users = validated_data.pop("user_set")
        group = super().create(validated_data)
        group.user_set.add(*users)
        return group

    @transaction.atomic()
    def update(self, instance, validated_data):
        users = validated_data.pop("user_set")
        old_users = instance.user_set.all()
        remove_users = [old_user for old_user in old_users if old_user not in users]
        add_users = [new_user for new_user in users if new_user not in old_users]
        instance.user_set.add(*add_users)
        instance.user_set.remove(*remove_users)
        return super().update(instance, validated_data)


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


class AtomicPermissionSerializer(serializers.ModelSerializer):
    requester = serializers.SlugRelatedField(
        source="user",
        slug_field="username",
        queryset=User.objects.all(),
        help_text=_("User to give the permission to"),
    )
    permission = serializers.CharField(
        max_length=255,
        help_text=_("Name of the permission"),
        default=zaken_inzien.name,
        source="atomic_permission.permission",
    )
    zaak = serializers.URLField(
        max_length=1000,
        help_text=_("URL of the zaak this permission applies to"),
        source="atomic_permission.object_url",
    )

    class Meta:
        model = UserAtomicPermission
        fields = (
            "id",
            "requester",
            "permission",
            "zaak",
            "start_date",
            "end_date",
            "comment",
            "reason",
        )
        extra_kwargs = {"id": {"read_only": True}, "reason": {"read_only": True}}


class GrantPermissionSerializer(AtomicPermissionSerializer):
    def validate(self, data):
        valid_data = super().validate(data)

        user = valid_data["user"]
        atomic_permission = valid_data["atomic_permission"]

        if (
            UserAtomicPermission.objects.select_related("atomic_permission")
            .filter(
                user=user,
                atomic_permission__object_url=atomic_permission["object_url"],
                atomic_permission__permission=atomic_permission["permission"],
            )
            .actual()
            .exists()
        ):
            raise serializers.ValidationError(
                _("User %(requester)s already has an access to zaak %(zaak)s")
                % {"requester": user.username, "zaak": atomic_permission["object_url"]}
            )

        return valid_data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        atomic_permission_data = validated_data.pop("atomic_permission")
        atomic_permission_data.update({"object_type": PermissionObjectTypeChoices.zaak})
        atomic_permission, created = AtomicPermission.objects.get_or_create(
            **atomic_permission_data
        )

        validated_data.update(
            {
                "atomic_permission": atomic_permission,
                "reason": PermissionReason.toegang_verlenen,
            }
        )
        user_atomic_permission = super().create(validated_data)

        # close pending access requests
        pending_requests = user_atomic_permission.user.initiated_requests.filter(
            zaak=atomic_permission.object_url, result=""
        ).actual()
        if pending_requests.exists():
            pending_requests.update(
                result=AccessRequestResult.approve,
                user_atomic_permission=user_atomic_permission,
            )

        # send email
        transaction.on_commit(
            lambda: send_email_to_requester(
                user_atomic_permission.user,
                zaak_url=atomic_permission.object_url,
                result=AccessRequestResult.approve,
                request=request,
                ui=True,
            )
        )
        return user_atomic_permission


class ZaakShortSerializer(APIModelSerializer):
    class Meta:
        model = Zaak
        fields = ("url", "identificatie", "bronorganisatie")
        extra_kwargs = {"url": {"read_only": True}}

    def to_representation(self, zaak_url: str):
        zaak = get_zaak(zaak_url=zaak_url)
        return super().to_representation(zaak)

    def to_internal_value(self, data):
        if "url" in data:
            return get_zaak(zaak_url=data["url"])

        return find_zaak(**data)


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
    zaak = ZaakShortSerializer(help_text=_("Zaak to request access for"))

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
    zaak = ZaakShortSerializer(help_text=_("Zaak to request access for"))

    class Meta:
        model = AccessRequest
        fields = ("url", "zaak", "comment", "requester")

    def validate(self, data):
        valid_data = super().validate(data)

        request = self.context["request"]
        requester = request.user
        zaak = valid_data["zaak"]

        if (
            UserAtomicPermission.objects.select_related("atomic_permission")
            .filter(
                user=requester,
                atomic_permission__object_url=zaak.url,
                atomic_permission__permission=zaken_inzien.name,
            )
            .actual()
            .exists()
        ):
            raise serializers.ValidationError(
                _("User %(requester)s already has an access to zaak %(zaak)s")
                % {"requester": requester.username, "zaak": zaak.url}
            )

        if (
            requester.initiated_requests.filter(zaak=zaak.url, result="")
            .actual()
            .exists()
        ):
            raise serializers.ValidationError(
                _(
                    "User %(requester)s already has an pending access request to zaak %(zaak)s"
                )
                % {"requester": requester.username, "zaak": zaak.url}
            )

        valid_data["requester"] = requester
        return valid_data

    def create(self, validated_data):
        validated_data["zaak"] = validated_data["zaak"].url
        return super().create(validated_data)


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
        required=False, help_text=_("Comment of the handler")
    )
    start_date = serializers.DateField(
        required=False, help_text=_("Start date of the access")
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

        if not valid_data.get("result"):
            raise serializers.ValidationError(
                _(
                    "'result' field should be defined when the access request is handled`"
                )
            )

        if self.instance and self.instance.result:
            raise serializers.ValidationError(
                _("This access request has already been handled")
            )

        request = self.context["request"]

        valid_data["handler"] = request.user
        valid_data["handled_date"] = date.today()

        return valid_data

    @transaction.atomic
    def update(self, instance, validated_data):
        handler_comment = validated_data.get("handler_comment", "")
        start_date = validated_data.get("start_date", date.today())
        end_date = validated_data.get("end_date")

        access_request = super().update(instance, validated_data)

        if access_request.result == AccessRequestResult.approve:
            # add permission definition
            atomic_permission, created = AtomicPermission.objects.get_or_create(
                object_url=access_request.zaak,
                object_type=PermissionObjectTypeChoices.zaak,
                permission=zaken_inzien.name,
            )
            user_atomic_permission = UserAtomicPermission.objects.create(
                atomic_permission=atomic_permission,
                user=access_request.requester,
                comment=handler_comment,
                reason=PermissionReason.toegang_verlenen,
                start_date=make_aware(
                    datetime.combine(start_date, datetime.min.time())
                ),
                end_date=make_aware(datetime.combine(end_date, datetime.min.time()))
                if end_date
                else None,
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


class GroupBlueprintSerializer(GroupPolymorphicSerializer):
    serializer_mapping = {
        object_type.name: object_type.blueprint_class
        for object_type in list(object_type_registry.values())
    }
    discriminator_field = "object_type"
    group_field = "policies"
    group_field_kwargs = {"many": True, "help_text": _("List of blueprint shapes")}

    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), help_text=_("Name of the role")
    )
    object_type = serializers.ChoiceField(
        choices=PermissionObjectTypeChoices.choices,
        help_text=_("Type of the permission object"),
    )


def generate_document_policies(zaaktype_policy: dict) -> List[dict]:
    zaaktype_omschrijving = zaaktype_policy.get("zaaktype_omschrijving")
    catalogus = zaaktype_policy.get("catalogus")

    if not zaaktype_omschrijving or not catalogus:
        return []

    # find zaaktype
    zaaktypen = get_zaaktypen(catalogus=catalogus, omschrijving=zaaktype_omschrijving)

    # find related iotypen
    document_policies = []
    for zaaktype in zaaktypen:
        if not zaaktype.informatieobjecttypen:
            continue

        iotypen = get_informatieobjecttypen_for_zaaktype(zaaktype)
        document_policies += [
            {
                "catalogus": iotype.catalogus,
                "iotype_omschrijving": iotype.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            }
            for iotype in iotypen
        ]
    return document_policies


class AuthProfileSerializer(serializers.HyperlinkedModelSerializer):
    blueprint_permissions = GroupBlueprintSerializer(
        many=True,
        source="group_permissions",
        help_text=_("List of blueprint permissions"),
    )

    class Meta:
        model = AuthorizationProfile
        fields = ("url", "uuid", "name", "blueprint_permissions")
        extra_kwargs = {"url": {"lookup_field": "uuid"}, "uuid": {"read_only": True}}

    @staticmethod
    def create_blueprint_permissions(group_permissions):
        blueprint_permissions = []

        for group in group_permissions:
            policies = group["policies"]

            # generate related iotype policies
            with parallel(max_workers=10) as executor:
                _document_policies = executor.map(generate_document_policies, policies)
                document_policies = sum(list(_document_policies), [])

            # create permissions
            for policy in policies:
                permission, created = BlueprintPermission.objects.get_or_create(
                    role=group["role"], object_type=group["object_type"], policy=policy
                )
                blueprint_permissions.append(permission)

            for policy in document_policies:
                permission, created = BlueprintPermission.objects.get_or_create(
                    role=group["role"],
                    object_type=PermissionObjectTypeChoices.document,
                    policy=policy,
                )
                blueprint_permissions.append(permission)

        return blueprint_permissions

    @transaction.atomic
    def create(self, validated_data):
        group_permissions = validated_data.pop("group_permissions")
        auth_profile = super().create(validated_data)

        blueprint_permissions = self.create_blueprint_permissions(group_permissions)
        auth_profile.blueprint_permissions.add(*blueprint_permissions)

        return auth_profile

    @transaction.atomic
    def update(self, instance, validated_data):
        group_permissions = validated_data.pop("group_permissions")
        auth_profile = super().update(instance, validated_data)

        auth_profile.blueprint_permissions.clear()
        blueprint_permissions = self.create_blueprint_permissions(group_permissions)
        auth_profile.blueprint_permissions.add(*blueprint_permissions)

        return auth_profile


def get_permission_choices():
    return [(name, permission.description) for name, permission in registry.items()]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.ListSerializer(
        child=serializers.ChoiceField(choices=get_permission_choices()),
        help_text=_("List of the permissions"),
    )

    class Meta:
        model = Role
        fields = ("id", "name", "permissions")


class PermissionSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, help_text="Name of the permission")
    description = serializers.CharField(help_text=_("Description of the permission"))
