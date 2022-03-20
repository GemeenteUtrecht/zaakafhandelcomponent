from typing import Dict, List

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, serializers

from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.accounts.models import User
from zac.core.services import get_zaak, get_zaaktype
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

    # Overwrite modelserializer unique validation at this point
    # Do this in the parent serializer
    order = serializers.IntegerField()

    class Meta:
        model = ChecklistQuestion
        fields = ("question", "order", "choices", "is_multiple_choice")


class ChecklistTypeSerializer(serializers.ModelSerializer):
    questions = ChecklistQuestionSerializer(
        many=True, source="checklistquestion_set", required=True
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
            "zaaktype_omschrijving",
        )
        extra_kwargs = {
            "uuid": {"read_only": True},
            "created": {"read_only": True},
            "modified": {"read_only": True},
            "zaaktype_catalogus": {"read_only": True},
            "zaaktype_omschrijving": {"read_only": True},
        }

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        zt = get_zaaktype(validated_data["zaaktype"])
        validated_data["zaaktype_omschrijving"] = zt.omschrijving
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

            # Set order of questions logically - monotonically increasing
            for order, question in enumerate(
                sorted(questions, key=lambda q: q["order"])
            ):
                question["order"] = order + 1

        return validated_data

    def create_questions(self, checklist_type: ChecklistType, questions: Dict):
        for question in questions:
            checklist_question = ChecklistQuestion.objects.create(
                checklist_type=checklist_type,
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
            checklist_type = super().create(validated_data)
        except ValidationError as err:
            raise exceptions.ValidationError(err.messages)

        self.create_questions(checklist_type, questions)
        return checklist_type

    @transaction.atomic
    def update(self, checklist_type, validated_data):
        # Delete all old questions
        checklist_type.checklistquestion_set.all().delete()

        # Create entirely new set of questions
        new_questions = validated_data.pop("checklistquestion_set")
        checklist_type = super().update(checklist_type, validated_data)
        self.create_questions(checklist_type, new_questions)
        return checklist_type


class ChecklistAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistAnswer
        fields = ("question", "answer", "created", "modified")


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
        validated_data = super().validate(attrs)
        if attrs.get("user_assignee") and attrs.get("group_assignee"):
            raise serializers.ValidationError(
                "A checklist can not be assigned to both a user and a group."
            )
        zaak = get_zaak(zaak_url=attrs["zaak"])
        zaaktype = get_zaaktype(zaak.zaaktype)
        checklist_type = attrs["checklist_type"]
        if not (
            checklist_type.zaaktype_omschrijving == zaaktype.omschrijving
            and checklist_type.zaaktype_catalogus == zaaktype.catalogus
        ):
            raise serializers.ValidationError(
                _(
                    "ZAAKTYPE of checklist_type is not related to the ZAAKTYPE of the ZAAK."
                )
            )

        return validated_data

    def _add_permissions_for_checklist_assignee(self, checklist):
        if checklist.user_assignee:
            add_permissions_for_checklist_assignee(checklist, checklist.user_assignee)
        if checklist.group_assignee:
            users = checklist.group_assignee.user_set.all()
            for user in users:
                add_permissions_for_checklist_assignee(checklist, user)

    def bulk_validate_answers(self, checklist: Checklist, answers: Dict):
        # Validate answers to multiple choice questions and
        # if they answer a question of the related checklist_type
        checklist_questions = (
            checklist.checklist_type.checklistquestion_set.prefetch_related(
                "questionchoice_set"
            )
        )
        questions = {question.question: question for question in checklist_questions}
        for answer in answers:
            if answer["question"] not in questions:
                raise serializers.ValidationError(
                    _(
                        f"Answer with question: `{answer['question']}` didn't answer a question of the related checklist_type: {checklist.checklist_type}."
                    )
                )

            if answer["answer"] and (question := questions.get(answer["question"])):
                if (valid_choices := question.valid_choice_values) and answer[
                    "answer"
                ] not in valid_choices:
                    raise serializers.ValidationError(
                        _(
                            f"Answer `{answer['answer']}` was not found in the options: {list(valid_choices)}."
                        )
                    )

    def bulk_create_answers(self, checklist: Checklist, answers: List):
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
            self.bulk_validate_answers(checklist, answers)
            self.bulk_create_answers(checklist, answers)

        self._add_permissions_for_checklist_assignee(checklist)
        return checklist

    def bulk_update_answers(self, checklist: Checklist, answers: List) -> List:
        questions_answers = {answer["question"]: answer["answer"] for answer in answers}
        answers_to_update = []
        updated_answers = []
        for answer in checklist.checklistanswer_set.all():
            if (
                new_answer := questions_answers.get(answer.question)
            ) and answer.answer != new_answer:
                answer.answer = new_answer
                answers_to_update.append(answer)
                updated_answers.append(answer.question)
        ChecklistAnswer.objects.bulk_update(answers_to_update, ["answer"])

        return updated_answers

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
            self.bulk_validate_answers(checklist, answers)
            updated_answers = self.bulk_update_answers(checklist, answers)
            create_answers = [
                answer
                for answer in answers
                if answer["question"] not in updated_answers
            ]
            self.bulk_create_answers(checklist, create_answers)

        # add permissions to assignee
        if grant_permissions:
            self._add_permissions_for_checklist_assignee(checklist)
        return checklist
