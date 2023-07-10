import datetime
from typing import Dict

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize
from rest_framework import serializers
from zgw_consumers.api_models.base import factory
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.api.fields import GroupSlugRelatedField, UserSlugRelatedField
from zac.accounts.models import User
from zac.contrib.objects.services import fetch_checklist, fetch_checklisttype
from zac.core.models import MetaObjectTypesConfig
from zac.core.services import (
    create_object,
    fetch_objecttype,
    relate_object_to_zaak,
    update_object_record_data,
)

from ..data import (
    Checklist,
    ChecklistAnswer,
    ChecklistQuestion,
    ChecklistType,
    QuestionChoice,
)


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
        queryset=User.objects.all(),
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
    meta = serializers.HiddenField(default=True)
    locked_by = UserSlugRelatedField(
        help_text=_("Checklist is locked by this user."),
        slug_field="username",
        allow_null=True,
        queryset=User.objects.all(),
        default=None,
    )

    class Meta:
        model = Checklist
        fields = ("answers", "meta", "locked_by")

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

        # Get objecttype associated to checklist
        checklist_obj_type_url = MetaObjectTypesConfig.get_solo().checklist_objecttype
        checklist_obj_type = fetch_objecttype(checklist_obj_type_url)

        # Get latest version of objecttype
        latest_version = fetch_objecttype(max(checklist_obj_type["versions"]))

        # Use data from request - the serializer was (ab)used to validate, not serialize.
        data = {
            **self.initial_data,
            "meta": True,
            "zaak": self.context["zaak"].url,
            "locked_by": None,
        }
        checklist = create_object(
            {
                "type": checklist_obj_type["url"],
                "record": {
                    "typeVersion": latest_version["version"],
                    "data": camelize(data, **api_settings.JSON_UNDERSCOREIZE),
                    "startAt": datetime.date.today().isoformat(),
                },
            }
        )
        relate_object_to_zaak(
            {
                "zaak": self.context["zaak"].url,
                "object": checklist["url"],
                "object_type": "overige",
                "object_type_overige": checklist_obj_type["name"],
                "object_type_overige_definitie": {
                    "url": latest_version["url"],
                    "schema": ".jsonSchema",
                    "objectData": ".record.data",
                },
                "relatieomschrijving": "Checklist van Zaak",
            }
        )

        return factory(Checklist, self.validated_data)

    def update(self) -> Checklist:
        data = {
            **self.initial_data,
            "zaak": self.context["zaak"].url,
            "meta": True,
            "lockedBy": None,
        }  # unlock the checklist at update
        checklist_obj = self.context["checklist_object"]
        update_object_record_data(
            object=checklist_obj,
            data=camelize(data, **api_settings.JSON_UNDERSCOREIZE),
            user=self.context["request"].user,
        )
        return factory(Checklist, self.validated_data)
