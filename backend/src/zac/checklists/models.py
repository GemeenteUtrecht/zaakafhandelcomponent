import uuid
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from ordered_model.models import OrderedModel

from .query import ChecklistAnswerQuerySet


class ChecklistMeta(models.Model):
    created = models.DateTimeField(_("Created"), auto_now_add=True)
    modified = models.DateTimeField(_("Modified"), auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ChecklistAnswer(ChecklistMeta):
    checklist = models.ForeignKey(
        "Checklist",
        on_delete=models.PROTECT,
        help_text=_("Checklist this answer is related to."),
    )
    question = models.TextField(
        _("Related question"),
        max_length=1000,
    )
    answer = models.TextField(_("Answer to the question"), blank=True)
    remarks = models.TextField(_("remarks"), blank=True)
    document = models.URLField(
        _("document URL"),
        max_length=1000,
        blank=True,
        help_text=_("Document in the Documents API."),
    )
    user_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("user assignee"),
        help_text=_("Person assigned to answer."),
        on_delete=models.SET_NULL,
    )
    group_assignee = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        verbose_name=_("group assignee"),
        help_text=_("Group assigned to answer."),
        on_delete=models.SET_NULL,
    )

    objects = ChecklistAnswerQuerySet.as_manager()

    class Meta:
        verbose_name = _("checklist answer")
        verbose_name_plural = _("checklist answers")

    def clean(self):
        # If the related question has related "choices"
        # check if the answer is one of the choices
        if self.answer:
            checklist_question = (
                self.checklist.checklisttype.checklistquestion_set.filter(
                    question=self.question
                )
            )
            if checklist_question.exists() and (
                choices := checklist_question[0]
                .questionchoice_set.all()
                .values_list("value", flat=True)
            ):
                if self.answer not in choices:
                    raise ValidationError(f"{self.answer} is not found in {choices}.")

    def save(self, *args, **kwargs):
        if self.user_assignee and self.group_assignee:
            raise ValidationError(
                "A checklist can not be assigned to both a user and a group."
            )
        return super().save(*args, **kwargs)


class QuestionChoice(ChecklistMeta):
    question = models.ForeignKey(
        "ChecklistQuestion",
        on_delete=models.CASCADE,
        help_text=_("Question the choices are related to."),
    )
    name = models.CharField(_("Human readable name of choice"), max_length=100)
    value = models.CharField(_("Value of choice"), max_length=100)

    class Meta:
        verbose_name = _("question choice")
        verbose_name_plural = _("question choices")
        unique_together = (("question", "name"), ("question", "value"))


class ChecklistQuestion(OrderedModel, ChecklistMeta):
    checklisttype = models.ForeignKey(
        "ChecklistType",
        on_delete=models.PROTECT,
        help_text=_("Checklisttype related to this question."),
    )
    question = models.TextField(
        _("Text of the question"),
        max_length=1000,
    )

    order_with_respect_to = "checklisttype"

    @property
    def is_multiple_choice(self) -> bool:
        return self.questionchoice_set.all().exists()

    @property
    def choices(self) -> Optional[QuerySet]:
        if choices := self.questionchoice_set.all().values_list("name", "value"):
            return choices
        return None

    @property
    def valid_choice_values(self) -> Optional[QuerySet]:
        if valid_choices := self.questionchoice_set.all().values_list(
            "value", flat=True
        ):
            return valid_choices
        return None

    class Meta:
        verbose_name = _("question")
        verbose_name_plural = _("questions")
        unique_together = (("question", "checklisttype"),)


class ChecklistType(ChecklistMeta):
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    zaaktype_catalogus = models.URLField(
        _("CATALOGUS of ZAAKTYPE"),
        max_length=1000,
        help_text=_("URL-reference to CATALOGUS of ZAAKTYPE."),
    )
    zaaktype_identificatie = models.CharField(
        _("ZAAKTYPE identificatie"),
        max_length=80,
        help_text=_("`identificatie` of ZAAKTYPE."),
        default="",
    )

    class Meta:
        verbose_name = _("checklisttype")
        verbose_name_plural = _("checklisttypes")
        unique_together = (("zaaktype_catalogus", "zaaktype_identificatie"),)

    def __str__(self):
        return _(
            "Checklisttype for ZAAKTYPE identificatie: {zt_id} within CATALOGUS: {zt_cat}"
        ).format(zt_id=self.zaaktype_identificatie, zt_cat=self.zaaktype_catalogus)


class Checklist(ChecklistMeta):
    zaak = models.URLField(
        _("ZAAK-URL"),
        max_length=1000,
        help_text=_("URL-reference to the ZAAK in its API."),
        unique=True,
    )
    checklisttype = models.ForeignKey(
        "ChecklistType", on_delete=models.PROTECT, help_text=_("Type of the checklist.")
    )

    class Meta:
        verbose_name = _("checklist")
        verbose_name_plural = _("checklists")
