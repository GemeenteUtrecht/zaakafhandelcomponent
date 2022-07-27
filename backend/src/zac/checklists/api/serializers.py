from typing import Dict, List

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, serializers

from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.accounts.models import User
from zac.core.services import get_zaaktype

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


class ChecklistQuestionSerializer(serializers.ModelSerializer):
    choices = QuestionChoiceSerializer(
        many=True, required=False, source="questionchoice_set"
    )

    # Overwrite modelserializer unique validation at this point
    # Do this in the parent serializer
    order = serializers.IntegerField()

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


class ChecklistTypeSerializer(serializers.ModelSerializer):
    questions = ChecklistQuestionSerializer(
        many=True, source="checklistquestion_set", required=True
    )
    zaaktype = serializers.URLField(
        help_text=_(
            "URL-reference to ZAAKTYPE. Zaaktype `identificatie` and `catalogus` will be derived from this."
        ),
        write_only=True,
    )

    class Meta:
        model = ChecklistType
        fields = (
            "uuid",
            "created",
            "modified",
            "questions",
            "zaaktype",
            "zaaktype_catalogus",
            "zaaktype_identificatie",
        )
        extra_kwargs = {
            "uuid": {"read_only": True},
            "created": {"read_only": True},
            "modified": {"read_only": True},
            "zaaktype_catalogus": {"read_only": True},
            "zaaktype_identificatie": {"read_only": True},
        }

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        zaaktype_url = validated_data.pop("zaaktype")
        zt = get_zaaktype(zaaktype_url)
        validated_data["zaaktype_identificatie"] = zt.identificatie
        validated_data["zaaktype_catalogus"] = zt.catalogus

        # validate uniqueness of question order
        if questions := validated_data.get("checklistquestion_set"):
            orders = {}
            for question in questions:
                if question["order"] in orders:
                    raise serializers.ValidationError(
                        _(
                            f"The order of the questions has to be unique. Question `{question['question']}` and question `{orders[question['order']]}` both have order `{question['order']}`."
                        )
                    )
                orders[question["order"]] = question["question"]

        return validated_data

    def create_questions(self, checklisttype: ChecklistType, questions: Dict):
        for question in questions:
            checklist_question = ChecklistQuestion.objects.create(
                checklisttype=checklisttype,
                question=question["question"],
                order=question["order"],
            )
            if choices := question.get("questionchoice_set"):
                QuestionChoice.objects.bulk_create(
                    [
                        QuestionChoice(
                            question=checklist_question,
                            name=choice["name"],
                            value=choice["value"],
                        )
                        for choice in choices
                    ]
                )

    @transaction.atomic
    def create(self, validated_data):
        questions = validated_data.pop("checklistquestion_set")
        try:
            checklisttype = super().create(validated_data)
        except ValidationError as err:
            raise exceptions.ValidationError(err.messages)

        self.create_questions(checklisttype, questions)
        return checklisttype

    @transaction.atomic
    def update(self, checklisttype, validated_data):
        # Delete all old questions
        checklisttype.checklistquestion_set.all().delete()

        # Create entirely new set of questions
        new_questions = validated_data.pop("checklistquestion_set")
        checklisttype = super().update(checklisttype, validated_data)
        self.create_questions(checklisttype, new_questions)
        return checklisttype


class BaseChecklistAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistAnswer
        fields = (
            "question",
            "answer",
            "created",
            "modified",
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
                "required": False,
                "min_length": 0,
                "help_text": _("Remarks in addition to the answer."),
            },
            "document": {
                "required": False,
                "min_length": 1,
                "help_text": _("URL-reference to document related to answer."),
            },
            "answer": {
                "required": True,
                "min_length": 0,
                "help_text": _("Answer to the question."),
            },
        }


class ReadChecklistAnswerSerializer(BaseChecklistAnswerSerializer):
    group_assignee = GroupSerializer(
        help_text=_("Group assigned to answer."),
    )
    user_assignee = UserSerializer(
        help_text=_("User assigned to answer."),
    )

    class Meta(BaseChecklistAnswerSerializer.Meta):
        model = BaseChecklistAnswerSerializer.Meta.model
        fields = BaseChecklistAnswerSerializer.Meta.fields


class WriteChecklistAnswerSerializer(BaseChecklistAnswerSerializer):
    group_assignee = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Group.objects.prefetch_related("user_set").all(),
        required=False,
        help_text=_("`name` of the group assigned to answer."),
        allow_null=True,
    )
    user_assignee = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        required=False,
        help_text=_("`username` of the user assigned to answer."),
        allow_null=True,
    )

    class Meta(BaseChecklistAnswerSerializer.Meta):
        model = BaseChecklistAnswerSerializer.Meta.model
        fields = BaseChecklistAnswerSerializer.Meta.fields


class BaseChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checklist
        fields = (
            "created",
            "answers",
        )


class ReadChecklistSerializer(BaseChecklistSerializer):
    answers = ReadChecklistAnswerSerializer(
        many=True,
        source="checklistanswer_set",
    )

    class Meta(BaseChecklistSerializer.Meta):
        model = BaseChecklistSerializer.Meta.model
        fields = BaseChecklistSerializer.Meta.fields


class WriteChecklistSerializer(BaseChecklistSerializer):
    answers = WriteChecklistAnswerSerializer(
        many=True,
        source="checklistanswer_set",
    )

    class Meta(BaseChecklistSerializer.Meta):
        model = BaseChecklistSerializer.Meta.model
        fields = BaseChecklistSerializer.Meta.fields

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        if not self.instance:
            zaak = self.context["zaak"]

            try:
                checklisttype = ChecklistType.objects.get(
                    zaaktype_identificatie=zaak.zaaktype.identificatie,
                    zaaktype_catalogus=zaak.zaaktype.catalogus,
                )
            except ChecklistType.DoesNotExist:
                raise serializers.ValidationError(
                    _("No checklisttype found for ZAAKTYPE of ZAAK.")
                )
            validated_data["zaak"] = zaak.url
            validated_data["checklisttype"] = checklisttype

        return validated_data

    def bulk_validate_answers(self, checklist: Checklist, answers: Dict):
        # Validate answers to multiple choice questions and
        # if they answer a question of the related checklisttype
        checklist_questions = (
            checklist.checklisttype.checklistquestion_set.prefetch_related(
                "questionchoice_set"
            )
        )
        questions = {question.question: question for question in checklist_questions}
        for answer in answers:
            if answer["question"] not in questions:
                raise serializers.ValidationError(
                    _(
                        "Answer with question: `{question}` didn't answer a question of the related checklisttype: {checklisttype}"
                    ).format(
                        question=answer["question"],
                        checklisttype=checklist.checklisttype,
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
                    "An answer to a checklist question can not be assigned to both a user and a group."
                )

        return answers

    def _add_permissions_for_checklist_assignee(
        self, checklist, answers: List[ChecklistAnswer]
    ):
        for answer in answers:
            if answer.user_assignee:
                add_permissions_for_checklist_assignee(checklist, answer.user_assignee)
            if answer.group_assignee:
                users = answer.group_assignee.user_set.all()
                for user in users:
                    add_permissions_for_checklist_assignee(checklist, user)

    @transaction.atomic
    def bulk_create_answers(
        self, checklist: Checklist, answers: List[Dict]
    ) -> List[ChecklistAnswer]:
        created_answers = ChecklistAnswer.objects.bulk_create(
            [ChecklistAnswer(checklist=checklist, **answer) for answer in answers]
        )
        self._add_permissions_for_checklist_assignee(checklist, created_answers)
        return created_answers

    def create(self, validated_data):
        answers = validated_data.pop("checklistanswer_set", False)
        checklist = super().create(validated_data)
        if answers:
            self.bulk_validate_answers(checklist, answers)
            self.bulk_create_answers(checklist, answers)

        return checklist

    @transaction.atomic
    def bulk_update_answers(
        self, checklist: Checklist, answers: List[Dict]
    ) -> List[ChecklistAnswer]:
        questions_answers = {answer["question"]: answer for answer in answers}
        answers_to_update = []
        for answer in checklist.checklistanswer_set.all():
            if (
                new_answer := questions_answers.get(answer.question)
            ) and answer.answer != new_answer:
                for attribute, value in new_answer.items():
                    setattr(answer, attribute, value)
                answers_to_update.append(answer)

        ChecklistAnswer.objects.bulk_update(
            answers_to_update,
            ["answer", "remarks", "document", "user_assignee", "group_assignee"],
        )
        self._add_permissions_for_checklist_assignee(checklist, answers_to_update)
        return answers_to_update

    def update(self, instance, validated_data):
        answers = validated_data.pop("checklistanswer_set", False)
        checklist = super().update(instance, validated_data)
        if answers:
            self.bulk_validate_answers(checklist, answers)
            updated_answers = self.bulk_update_answers(checklist, answers)
            create_answers = [
                answer
                for answer in answers
                if answer["question"] not in [ans.question for ans in updated_answers]
            ]
            self.bulk_create_answers(checklist, create_answers)

        return checklist
