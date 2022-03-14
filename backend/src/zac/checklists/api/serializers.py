from typing import Dict, Union

from django.contrib.auth.models import Group
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.accounts.models import User
from zac.utils.validators import ImmutableFieldValidator

from ..models import (
    Checklist,
    ChecklistAnswer,
    ChecklistQuestion,
    ChecklistType,
    QuestionChoice,
)
from .permission_loaders import add_permissions_for_checklist_assignee


class QuestionChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionChoice
        fields = ("name", "value")


class ChecklistQuestionSerializer(serializers.ModelSerializer):
    choices = QuestionChoiceSerializer(
        many=True, required=False, source="questionchoice_set"
    )

    class Meta:
        model = ChecklistQuestion
        fields = ("pk", "question", "order", "choices", "is_multiple_choice")


class ChecklistTypeSerializer(serializers.ModelSerializer):
    questions = ChecklistQuestionSerializer(many=True, source="checklistquestion_set")

    class Meta:
        model = ChecklistType
        fields = (
            "uuid",
            "questions",
        )


class ChecklistAnswerSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(
        help_text=_("Primary key of related question"),
        queryset=ChecklistQuestion.objects.all(),
    )

    class Meta:
        model = ChecklistAnswer
        fields = ("question", "answer")

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        question = validated_data["question"]
        if (valid_choices := list(question.valid_choice_values)) and attrs[
            "answer"
        ] not in valid_choices:
            raise serializers.ValidationError(
                _(
                    f"Answer `{attrs['answer']}` was not found in the options: {valid_choices}."
                )
            )
        return attrs


class BaseChecklistSerializer(serializers.ModelSerializer):
    answers = ChecklistAnswerSerializer(
        many=True,
        source="checklistanswer_set",
    )
    checklist_type = serializers.SlugRelatedField(
        slug_field="uuid",
        queryset=ChecklistType.objects.all(),
        required=True,
        help_text=_("`uuid` of the checklist_type."),
    )

    class Meta:
        model = Checklist
        fields = (
            "url",
            "created",
            "checklist_type",
            "group_assignee",
            "user_assignee",
            "zaak",
            "answers",
        )
        extra_kwargs = {
            "url": {
                "view_name": "checklist-detail",
            },
        }


class ReadChecklistSerializer(BaseChecklistSerializer):
    group_assignee = GroupSerializer(
        required=False,
        help_text=_("Group assigned to checklist."),
    )
    user_assignee = UserSerializer(
        required=False,
        help_text=_("User assigned to checklist."),
    )

    class Meta(BaseChecklistSerializer.Meta):
        model = BaseChecklistSerializer.Meta.model
        fields = BaseChecklistSerializer.Meta.fields


class ChecklistSerializer(BaseChecklistSerializer):
    group_assignee = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Group.objects.prefetch_related("user_set").all(),
        required=False,
        help_text=_("Name of the group."),
    )
    user_assignee = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        required=False,
        help_text=_("`username` of the user."),
    )

    class Meta(BaseChecklistSerializer.Meta):
        model = BaseChecklistSerializer.Meta.model
        fields = BaseChecklistSerializer.Meta.fields
        extra_kwargs = {
            "zaak": {"validators": (ImmutableFieldValidator(),)},
            "checklist_type": {"validators": (ImmutableFieldValidator(),)},
        }

    def validate(self, attrs):
        if attrs.get("user_assignee") and attrs.get("group_assignee"):
            raise serializers.ValidationError(
                "A checklist can not be assigned to both a user and a group."
            )
        return attrs

    def _add_permissions_for_checklist_assignee(self, checklist):
        if checklist.user_assignee:
            add_permissions_for_checklist_assignee(checklist, checklist.user_assignee)
        if checklist.group_assignee:
            users = checklist.group_assignee.user_set.all()
            for user in users:
                add_permissions_for_checklist_assignee(checklist, user)

    def bulk_create_answers(
        self, checklist: Checklist, answers: Dict[str, Union[str, ChecklistQuestion]]
    ):
        ChecklistAnswer.objects.bulk_create(
            [
                ChecklistAnswer(
                    checklist=checklist,
                    question=answer["question"],
                    answer=answer["answer"],
                )
                for answer in answers
            ]
        )

    @transaction.atomic
    def create(self, validated_data):
        answers = validated_data.pop("checklistanswer_set", False)
        checklist = super().create(validated_data)
        if answers:
            self.bulk_create_answers(checklist, answers)

        self._add_permissions_for_checklist_assignee(checklist)
        return checklist

    @transaction.atomic
    def update(self, instance, validated_data):
        user_assignee = validated_data.get("user_assignee")
        group_assignee = validated_data.get("group_assignee")
        grant_permissions = (
            user_assignee
            or group_assignee
            and (
                user_assignee != instance.user_assignee
                or group_assignee != instance.group_assignee
            )
        )
        if user_assignee:
            validated_data["group_assignee"] = None
        if group_assignee:
            validated_data["user_assignee"] = None

        answers = validated_data.pop("checklistanswer_set", False)
        checklist = super().update(instance, validated_data)
        if answers:
            self.bulk_create_answers(checklist, answers)

        # add permissions to assignee
        if grant_permissions:
            self._add_permissions_for_checklist_assignee(checklist)
        return checklist
