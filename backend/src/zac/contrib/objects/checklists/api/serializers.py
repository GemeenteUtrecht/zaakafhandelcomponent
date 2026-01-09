from typing import Dict, Tuple

from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize
from rest_framework import serializers
from zgw_consumers.api_models.base import factory

from zac.accounts.api.fields import UserSlugRelatedField
from zac.accounts.api.serializers import UserSerializer
from zac.accounts.models import User
from zac.contrib.objects.services import (
    create_meta_object_and_relate_to_zaak,
    fetch_checklist,
    fetch_checklisttype,
)
from zac.core.services import update_object_record_data
from zac.tests.compat import APIModelSerializer

from ...serializers import (
    MetaObjectGroupSerializerSlugRelatedField,
    MetaObjectUserSerializerSlugRelatedField,
)
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
    group_assignee = MetaObjectGroupSerializerSlugRelatedField(
        slug_field="name",
        queryset=Group.objects.all(),
        help_text=_("`name` of the group assigned to answer."),
        allow_null=True,
        default=None,
    )
    user_assignee = MetaObjectUserSerializerSlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        help_text=_("`username` of the user assigned to answer."),
        allow_null=True,
        default=None,
    )
    created = serializers.DateTimeField(
        help_text=_("Datetime answer was given."),
        read_only=True,
    )

    class Meta:
        model = ChecklistAnswer
        fields = (
            "question",
            "answer",
            "created",
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
                "allow_blank": True,
                "default": "",
            },
            "document": {
                "help_text": _("URL-reference to document related to answer."),
                "allow_blank": True,
                "default": "",
            },
            "answer": {
                "min_length": 0,
                "help_text": _("Answer to the question."),
                "allow_blank": True,
                "default": "",
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
        else:
            raise RuntimeError(
                "This serializer requires the ZAAK to be passed into its context."
            )

        validated_data["answers"] = self.bulk_validate_answers(
            validated_data["answers"]
        )
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
            answer["created"] = timezone.now().isoformat()

        # Check if all questions are given (unanswered questions should be empty)
        questions_answered = [answer["question"] for answer in answers]
        for question in questions.keys():
            if question not in questions_answered:
                raise serializers.ValidationError(
                    _("Question {question} not answered.").format(question=question)
                )

        return answers

    def create(self) -> Tuple[Checklist, bool]:
        # Final check before creation
        checklist = fetch_checklist(self.context["zaak"])
        if checklist:
            return checklist, False

        data = {**self.data, "zaak": self.context["zaak"].url, "locked": False}
        create_meta_object_and_relate_to_zaak(
            "checklist", data, self.context["zaak"].url
        )

        return (
            factory(
                Checklist,
                data,
            ),
            True,
        )

    def update(self) -> bool:
        assert self.is_valid(), "Serializer must be valid."

        old_answers = {answer["question"]: answer for answer in self.data["answers"]}

        # check if object changed - "autosave" creates many duplicate records
        new_answers = {
            answer["question"]: answer
            for answer in ChecklistAnswerSerializer(
                self.validated_data["answers"], many=True
            ).data
        }

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

        # set update flag to false until change has been detected
        update = False
        for question, new_answer in new_answers.items():
            answer = {}
            answer["answer"] = new_answer["answer"]
            if question not in old_answers:
                update = True
                new_checklist_data["answers"].append(new_answer)

            elif (old_answer := old_answers.get(question)) and any(
                [
                    new_answer.get(key, None) != old_answer.get(key, None)
                    for key in change_in_keys
                ]
            ):
                update = True
                new_checklist_data["answers"].append(new_answer)
            else:
                new_checklist_data["answers"].append(old_answer)

        data = {
            "answers": new_checklist_data["answers"],
            "zaak": self.context["zaak"].url,
            "locked": False,
        }
        if update:
            # unlock the checklist at update
            update_object_record_data(
                object=self.context["checklist_object"],
                data=camelize(data, **api_settings.JSON_UNDERSCOREIZE),
                user=self.context["request"].user,
            )
        return factory(
            Checklist,
            data,
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
