from copy import deepcopy
from typing import Dict

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize, underscoreize
from rest_framework import serializers
from zgw_consumers.api_models.base import factory
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.api.fields import GroupSlugRelatedField, UserSlugRelatedField
from zac.accounts.api.serializers import UserSerializer
from zac.accounts.models import User
from zac.contrib.objects.services import (
    create_meta_object_and_relate_to_zaak,
    fetch_checklist,
    fetch_checklisttype,
)
from zac.core.services import update_object_record_data

from ..data import (
    Checklist,
    ChecklistAnswer,
    ChecklistQuestion,
    ChecklistType,
    QuestionChoice,
)
from ..models import ChecklistLock


class QuestionChoiceSerializer(APIModelSerializer):
    class Meta:
        model = QuestionChoice
        fields = ("name", "value")
        extra_kwargs = {
            "name": {
                "required": True,
                "min_length": 1,
                "help_text": _("Name of choice."),
            },
            "value": {
                "required": True,
                "min_length": 1,
                "help_text": _("Value of choice."),
            },
        }


class ChecklistQuestionSerializer(APIModelSerializer):
    choices = QuestionChoiceSerializer(many=True, required=False)
    is_multiple_choice = serializers.SerializerMethodField(source="choices")

    class Meta:
        model = ChecklistQuestion
        fields = ("question", "order", "choices", "is_multiple_choice")
        extra_kwargs = {
            "question": {
                "required": True,
                "min_length": 1,
                "help_text": _("Question for user to answer."),
            },
            "order": {
                "required": True,
                "help_text": _("Order of question in checklist."),
            },
        }

    def get_is_multiple_choice(self, obj) -> bool:
        return bool(obj.choices)


class ChecklistTypeSerializer(APIModelSerializer):
    questions = ChecklistQuestionSerializer(many=True, required=True)

    class Meta:
        model = ChecklistType
        fields = ("questions",)


class ChecklistAnswerSerializer(APIModelSerializer):
    group_assignee = GroupSlugRelatedField(
        slug_field="name",
        queryset=Group.objects.prefetch_related("user_set").all(),
        required=False,
        help_text=_("`name` of the group assigned to answer."),
        allow_null=True,
    )
    user_assignee = UserSlugRelatedField(
        slug_field="username",
        queryset=User.objects.prefetch_related("groups").all(),
        required=False,
        help_text=_("`username` of the user assigned to answer."),
        allow_null=True,
    )

    class Meta:
        model = ChecklistAnswer
        fields = (
            "question",
            "answer",
            "remarks",
            "document",
            "group_assignee",
            "user_assignee",
        )
        extra_kwargs = {
            "question": {
                "required": True,
                "min_length": 1,
                "help_text": _("The question related to the answer."),
            },
            "remarks": {
                "help_text": _("Remarks in addition to the answer."),
                "required": False,
                "allow_blank": True,
            },
            "document": {
                "help_text": _("URL-reference to document related to answer."),
                "required": False,
                "allow_blank": True,
            },
            "answer": {
                "required": True,
                "min_length": 0,
                "help_text": _("Answer to the question."),
                "allow_blank": True,
            },
        }


class ChecklistSerializer(APIModelSerializer):
    answers = ChecklistAnswerSerializer(
        many=True,
    )
    locked_by = UserSerializer(
        help_text=_("Checklist is locked by this user."),
        allow_null=True,
        source="get_locked_by",
        read_only=True,
    )
    zaak = serializers.URLField(
        read_only=True, help_text=_("URL-reference of ZAAK checklist belongs to.")
    )

    class Meta:
        model = Checklist
        fields = ("answers", "locked_by", "zaak", "locked")
        extra_kwargs = {"locked": {"read_only": True}}

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if zaak := self.context.get("zaak"):
            validated_data["zaak"] = zaak.url
            self.bulk_validate_answers(validated_data["answers"])

        return validated_data

    def bulk_validate_answers(self, answers: Dict):
        # Validate answers to multiple choice questions and
        # if they answer a question of the related checklisttype
        checklisttype = fetch_checklisttype(self.context["zaak"].zaaktype)
        if not checklisttype:
            raise serializers.ValidationError(_("Checklisttype can not be found."))

        questions = {
            question.question: question for question in checklisttype.questions
        }
        for answer in answers:
            if answer["question"] not in questions:
                raise serializers.ValidationError(
                    _(
                        "Answer with question: `{question}` didn't answer a question of the related checklisttype."
                    ).format(
                        question=answer["question"],
                    )
                )

            if answer["answer"] and (question := questions.get(answer["question"])):
                if (valid_choices := question.valid_choice_values) and answer[
                    "answer"
                ] not in valid_choices:
                    raise serializers.ValidationError(
                        _(
                            "Answer `{answer}` was not found in the options: {choices}."
                        ).format(answer=answer["answer"], choices=list(valid_choices))
                    )
            if answer.get("user_assignee") and answer.get("group_assignee"):
                raise serializers.ValidationError(
                    _(
                        "An answer to a checklist question can not be assigned to both a user and a group."
                    )
                )

        # Check if all questions are given (unanswered questions should be empty)
        questions_answered = [answer["question"] for answer in answers]
        for question in questions.keys():
            if question not in questions_answered:
                raise serializers.ValidationError(
                    _("Question {question} not answered.").format(question=question)
                )
        return answers

    def create(self) -> Checklist:
        # Final check before creation
        checklist = fetch_checklist(self.context["zaak"])
        if checklist:
            raise serializers.ValidationError(_("Checklist already exists."))

        # Use data from request - the serializer was (ab)used to validate, not serialize.
        data = {**self.initial_data, "zaak": self.context["zaak"].url, "locked": False}
        create_meta_object_and_relate_to_zaak(
            "checklist", data, self.context["zaak"].url
        )

        return factory(
            Checklist,
            {**self.validated_data, "zaak": self.context["zaak"].url, "locked": False},
        )

    def update(self) -> bool:
        checklist_obj = self.context["checklist_object"]
        # check if object changed - "autosave" creates many similar records
        # underscoreize data from objects api
        old_answers = {
            answer["question"]: answer
            for answer in underscoreize(
                checklist_obj["record"]["data"]["answers"],
                **api_settings.JSON_UNDERSCOREIZE,
            )
        }
        # deepcopy dictionary to prevent changes being made to initial_data (not sure if even possible)
        new_answers = {
            answer["question"]: answer
            for answer in deepcopy(self.initial_data["answers"])
        }

        # set update flag to false until change has been detected
        update = False

        # create new dictionary to be uploaded to objects in case change is detected
        new_checklist_data = {"answers": []}

        # changes in these keys are 'key' - haha - to proceed with update
        change_in_keys = [
            "answer",
            "user_assignee",
            "group_assignee",
            "remarks",
            "document",
        ]
        for question, old_answer in old_answers.items():
            if (new_answer := new_answers.get(question)) and any(
                [new_answer.get(key) != old_answer.get(key) for key in change_in_keys]
            ):
                update = True
                new_checklist_data["answers"].append(new_answer)
            else:
                new_checklist_data["answers"].append(old_answer)

        data = {}
        if update:
            data = {
                **new_checklist_data,
                "zaak": self.context["zaak"].url,
            }  # unlock the checklist at update
            update_object_record_data(
                object=checklist_obj,
                data=camelize(data, **api_settings.JSON_UNDERSCOREIZE),
                user=self.context["request"].user,
            )
        return factory(
            Checklist,
            {**self.validated_data, "zaak": self.context["zaak"].url, "locked": False},
        )


class ChecklistLockSerializer(serializers.ModelSerializer):
    user = UserSlugRelatedField(
        slug_field="username",
        queryset=User.objects.prefetch_related("groups").all(),
        allow_null=True,
        required=True,
    )

    class Meta:
        model = ChecklistLock
        fields = ("url", "user", "zaak", "zaak_identificatie")
