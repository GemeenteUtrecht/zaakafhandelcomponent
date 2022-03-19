import uuid
from tabnanny import verbose
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _


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
    answer = models.TextField(_("Answer to the question"), max_length=1000, blank=True)

    class Meta:
        verbose_name = _("checklist answer")
        verbose_name_plural = _("checklist answers")

    def clean(self):
        # If the related question has related "choices"
        # check if the answer is one of the choices
        if self.answer:
            checklist_question = (
                self.checklist.checklist_type.checklistquestion_set.filter(
                    question=self.question
                )
            )
            if checklist_question.exists() and (
                choices := checklist_question.questionchoice_set.all().values_list(
                    "value", flat=True
                )
            ):
                if self.answer not in choices:
                    raise ValidationError(f"{self.answer} is not found in {choices}.")


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


class ChecklistQuestion(ChecklistMeta):
    checklist_type = models.ForeignKey(
        "ChecklistType",
        on_delete=models.PROTECT,
        help_text=_("Checklist type related to this question."),
    )
    question = models.TextField(
        _("Text of the question"),
        max_length=1000,
    )
    order = models.PositiveSmallIntegerField(
        _("Order"),
        help_text=_(
            "Order of the questions as they should be presented in the checklist."
        ),
    )

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
        unique_together = (("question", "checklist_type"), ("checklist_type", "order"))


class ChecklistType(ChecklistMeta):
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    zaaktype_catalogus = models.URLField(
        _("CATALOGUS of ZAAKTYPE"),
        max_length=1000,
        help_text=_("URL-referentie naar de CATALOGUS van het ZAAKTYPE."),
    )
    zaaktype_omschrijving = models.CharField(
        _("Omschrijving"),
        max_length=80,
        help_text=_("Omschrijving van het ZAAKTYPE."),
    )
    zaaktype = models.URLField(
        _("ZAAKTYPE-URL"),
        max_length=1000,
        help_text=_("URL-referentie naar het ZAAKTYPE."),
    )

    class Meta:
        verbose_name = _("checklist type")
        verbose_name_plural = _("checklist types")
        unique_together = (("zaaktype_catalogus", "zaaktype_omschrijving"),)

    def __str__(self):
        return f"Checklist type of {self.zaaktype_omschrijving} within {self.zaaktype_catalogus}"


class Checklist(ChecklistMeta):
    zaak = models.URLField(
        _("ZAAK-URL"),
        max_length=1000,
        help_text=_("URL-reference to the ZAAK in its API."),
        unique=True,
    )
    checklist_type = models.ForeignKey(
        "ChecklistType", on_delete=models.PROTECT, help_text=_("Type of the checklist.")
    )
    user_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("user assignee"),
        help_text=_("Person responsible for managing this checklist."),
        on_delete=models.SET_NULL,
    )
    group_assignee = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        verbose_name=_("group assignee"),
        help_text=_("Group responsible for managing this checklist."),
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = _("checklist")
        verbose_name_plural = _("checklists")

    def save(self, *args, **kwargs):
        if self.user_assignee and self.group_assignee:
            raise ValidationError(
                "A checklist can not be assigned to both a user and a group."
            )
        return super().save(*args, **kwargs)
