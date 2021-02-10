from dataclasses import dataclass
from typing import List, NoReturn, Optional

from django.urls import reverse

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import User
from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, register, usertask_context_serializer
from zac.contrib.dowc.constants import DocFileTypes


class ValidSignDocumentSerializer(APIModelSerializer):
    drc_url = serializers.SerializerMethodField()
    read_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "beschrijving",
            "bestandsnaam",
            "bestandsomvang",
            "drc_url",
            "read_url",
            "versie",
        )

    def get_drc_url(self, obj) -> str:
        return obj.url

    def get_read_url(self, obj) -> str:
        return reverse(
            "dowc:request-doc",
            kwargs={
                "bronorganisatie": obj.bronorganisatie,
                "identificatie": obj.identificatie,
                "purpose": DocFileTypes.read,
            },
        )


@dataclass
class ValidSignContext(Context):
    documenten: List[Document]


@usertask_context_serializer
class ValidSignContextSerializer(serializers.Serializer):
    documenten = ValidSignDocumentSerializer(many=True)


#
# Write serializer
#


class ValidSignUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
        )
        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "first_name": {"required": False},
            "last_name": {"required": False},
        }


class ValidSignTaskSerializer(serializers.Serializer):
    assigned_users = ValidSignUserSerializer(many=True)
    selected_documents = serializers.ListField(
        child=serializers.URLField(), required=False
    )

    def is_valid(self, raise_exception=True):
        super().is_valid(raise_exception=raise_exception)
        errors = self.validate_users_are_unique()
        errors.extend(self.validate_users())
        if errors and raise_exception:
            raise serializers.ValidationError(errors)

        return not bool(errors)

    def validate_users_are_unique(self) -> List:
        unique_assigned_users = [
            dict(assigned_user_set)
            for assigned_user_set in set(
                frozenset(assigned_user.items())
                for assigned_user in self.validated_data["assigned_users"]
            )
        ]
        errors = []
        if len(unique_assigned_users) < len(self.validated_data["assigned_users"]):
            errors.append(
                serializers.ValidationError(_("Please select a set of unique signers."))
            )
        return errors

    def validate_users(self) -> List:
        errors = []
        assigned_users = self.validated_data["assigned_users"]
        if not assigned_users:
            errors.append(
                serializers.ValidationError(_("Please select at least one signer."))
            )
        else:
            all_users = User.objects.all().values(
                "username", "first_name", "last_name", "email"
            )
            all_usernames = [user.username for user in all_users]
            invalid_usernames = [
                user["usernames"] not in usernames for user in assigned_users
            ]
            for au in assigned_users:
                if not au["username"] or au["username"] not in all_usernames:
                    if not au["first_name"] or not au["last_name"] or not au["email"]:
                        errors.append(
                            serializers.ValidationError(
                                _(
                                    "User with username: {username} is unknown. Please provide all other details."
                                ).format(username=au["username"])
                            )
                        )
                else:
                    user_in_db = all_users[au["username"]]
                    if not user_in_db["email"]:
                        errors.append(
                            serializers.ValidationError(
                                _(
                                    "Email address for user with username: {username} is unknown. Please provide their email address."
                                ).format(username=au["username"])
                            )
                        )

                    if not user_in_db["first_name"]:
                        errors.append(
                            serializers.ValidationError(
                                _(
                                    "First name for user with username: {username} is unknown. Please provide their first name."
                                ).format(username=au["username"])
                            )
                        )

                    if not user_in_db["last_name"]:
                        errors.append(
                            serializers.ValidationError(
                                _(
                                    "Last name for user with username: {username} is unknown. Please provide their last name."
                                ).format(username=au["username"])
                            )
                        )
        return errors

    def get_process_variables(self) -> dict:
        signers = []
        for signer_data in self.validated_data["assigned_users"]:
            if not signer_data:  # empty form
                continue

            signers.append(
                {
                    "email": signer_data["email"],
                    "firstName": signer_data["first_name"],
                    "lastName": signer_data["last_name"],
                }
            )

        return {
            "signers": signers,
        }

    def on_task_submission(self) -> NoReturn:
        pass


@register(
    "zac:validSign:configurePackage",
    ValidSignContextSerializer,
    ValidSignTaskSerializer,
)
def get_context(task: Task) -> ValidSignContext:
    process_instance = get_process_instance(task.process_instance_id)
    zaak_url = get_process_zaak_url(process_instance)
    zaak = get_zaak(zaak_url=zaak_url)
    zaaktype = fetch_zaaktype(zaak.zaaktype)
    documents = get_documenten(zaak)
    return ValidSignContext(
        documenten=documents,
    )
