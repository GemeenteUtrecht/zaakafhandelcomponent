from dataclasses import dataclass
from typing import Dict, List, Optional

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import User
from zac.api.context import get_zaak_context
from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, register, usertask_context_serializer
from zac.core.api.fields import SelectDocumentsField
from zac.core.camunda.select_documents.serializers import DocumentSerializer


@dataclass
class ValidSignContext(Context):
    documents: List[Document]


@usertask_context_serializer
class ValidSignContextSerializer(APIModelSerializer):
    documents = DocumentSerializer(many=True)

    class Meta:
        model = ValidSignContext
        fields = ("documents",)


#
# Write serializer
#


class ValidSignUserSerializer(serializers.Serializer):
    username = serializers.CharField(
        label=_("username"),
        help_text=_("Username of signer."),
        required=False,
    )
    email = serializers.EmailField(
        label=_("email address"),
        help_text=_("Email of signer."),
        required=False,
    )
    first_name = serializers.CharField(
        label=_("first name"),
        help_text=_("First name of signer."),
        required=False,
    )
    last_name = serializers.CharField(
        label=_("last name"),
        help_text=_("Last name of signer."),
        required=False,
    )


class ValidSignTaskSerializer(serializers.Serializer):
    """
    Serialize assigned users and selected documents.
    Must have a ``task`` in its ``context``.
    """

    selected_documents = SelectDocumentsField()
    assigned_users = ValidSignUserSerializer(many=True)

    def get_zaak_from_context(self):
        zaak_context = get_zaak_context(self.context["task"])
        return zaak_context.zaak

    def validate_assigned_users(self, assigned_users) -> Optional[Dict]:
        if not assigned_users:
            raise serializers.ValidationError(
                _("Please select at least one signer."), code="empty-signers"
            )

        else:
            unique_assigned_users = [
                dict(assigned_user_set)
                for assigned_user_set in set(
                    frozenset(assigned_user.items()) for assigned_user in assigned_users
                )
            ]
            if len(unique_assigned_users) < len(assigned_users):
                raise serializers.ValidationError(
                    _("Please select a set of unique signers."), code="unique-signers"
                )

        all_users = {
            user["username"]: user
            for user in User.objects.all().values(
                "username", "first_name", "last_name", "email"
            )
        }
        all_usernames = all_users.keys()
        for au in assigned_users:
            if not au.get("username") or au.get("username") not in all_usernames:
                if (
                    not au.get("first_name")
                    or not au.get("last_name")
                    or not au.get("email")
                ):
                    raise serializers.ValidationError(
                        _(
                            "User with username: {username} is unknown. Please provide all other details."
                        ).format(username=au["username"]),
                        code="missing-signer-details",
                    )
            else:
                user_in_db = all_users[au["username"]]
                if not user_in_db["email"] and not au["email"]:
                    raise serializers.ValidationError(
                        _(
                            "Email address for user with username: {username} is unknown. Please provide their email address."
                        ).format(username=au["username"]),
                        code="unknown-email",
                    )
                else:
                    au["email"] = user_in_db["email"]

                if not user_in_db["first_name"] and not au["first_name"]:
                    raise serializers.ValidationError(
                        _(
                            "First name for user with username: {username} is unknown. Please provide their first name."
                        ).format(username=au["username"]),
                        code="unknown-first-name",
                    )
                else:
                    au["first_name"] = user_in_db["first_name"]

                if not user_in_db["last_name"] and not au["last_name"]:
                    raise serializers.ValidationError(
                        _(
                            "Last name for user with username: {username} is unknown. Please provide their last name."
                        ).format(username=au["username"]),
                        code="unknown-last-name",
                    )
                else:
                    au["last_name"] = user_in_db["last_name"]

        return assigned_users

    def get_process_variables(self) -> dict:
        assert self.is_valid(), "serializer must be valid"
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
            "documenten": self.validated_data["selected_documents"],
        }

    def on_task_submission(self) -> None:
        pass


@register(
    "zac:validSign:configurePackage",
    ValidSignContextSerializer,
    ValidSignTaskSerializer,
)
def get_context(task: Task) -> ValidSignContext:
    zaak_context = get_zaak_context(task, require_documents=True)
    return ValidSignContext(
        documents=zaak_context.documents,
    )
