import uuid
from typing import Optional

from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _


class KillableTask(models.Model):
    """
    Holds the name of a camunda task that can be canceled.

    """

    name = models.CharField(_("task name"), max_length=100, unique=True)

    class Meta:
        verbose_name = _("camunda task")
        verbose_name_plural = _("camunda tasks")

    def __str__(self):
        return self.name


class CamundaStartProcessForm(models.Model):
    """
    Configuration needed to start a process for a ZAAK of ZAAKTYPE.

    """

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    zaaktype_catalogus = models.URLField(
        _("CATALOGUS of ZAAKTYPE"),
        max_length=1000,
        help_text=_("URL-reference to the CATALOGUS of the ZAAKTYPE."),
    )
    zaaktype_identificatie = models.CharField(
        _("identificatie"),
        max_length=80,
        help_text=_("`identificatie` of the ZAAKTYPE."),
    )
    process_definition_key = models.CharField(
        _("process definition key"),
        max_length=100,
        unique=True,
        help_text=_("Key of camunda process definition linked to this form."),
    )

    class Meta:
        verbose_name = _("camunda start process form")
        verbose_name_plural = _("camunda start process forms")
        unique_together = (("zaaktype_catalogus", "zaaktype_identificatie"),)


class CamundaStartProcessFormMixin(models.Model):
    camunda_start_process_form = models.ForeignKey(
        CamundaStartProcessForm,
        help_text=_("Related camunda start process form."),
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class FieldMixin(models.Model):
    label = models.CharField(
        _("label"), max_length=100, help_text=_("The label that will be shown.")
    )
    value = models.CharField(
        _("value"),
        max_length=100,
        help_text=_("The value that will be used internally."),
    )

    class Meta:
        abstract = True


class ProcessEigenschap(CamundaStartProcessFormMixin, FieldMixin):
    eigenschapnaam = models.CharField(
        _("eigenschapnaam"),
        max_length=20,
        help_text=_("The name of the EIGENSCHAP"),
        unique=True,
    )

    @property
    def is_multiple_choice(self) -> bool:
        return self.processeigenschapchoice_set.all().exists()

    @property
    def choices(self) -> Optional[QuerySet]:
        if choices := self.processeigenschapchoice_set.all().values_list(
            "label", "value"
        ):
            return choices
        return None

    @property
    def valid_choice_values(self) -> Optional[QuerySet]:
        if valid_choices := self.processeigenschapchoice_set.all().values_list(
            "value", flat=True
        ):
            return valid_choices
        return None

    class Meta:
        verbose_name = _("Process EIGENSCHAP")
        verbose_name_plural = _("Process EIGENSCHAPpen")


class ProcessEigenschapChoice(FieldMixin):
    process_eigenschap = models.ForeignKey(
        ProcessEigenschap,
        help_text=_("Choices that can be selected."),
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Choice")
        verbose_name_plural = _("Choices")


class ProcessInformatieObject(CamundaStartProcessFormMixin, FieldMixin):
    informatieobjecttype_omschrijving = models.CharField(
        _("INFORMATIEOBJECTTYPE omschrijving"), max_length=100
    )
    allow_multiple = models.BooleanField(
        _(
            "Allow multiple documents",
            help_text=_(
                "A boolean flag to indicate whether a user is allowed to add more than 1 document."
            ),
        )
    )

    class Meta:
        verbose_name = _("Process INFORMATIEOBJECT")
        verbose_name_plural = _("Process INFORMATIEOBJECTen")


class ProcessRol(CamundaStartProcessFormMixin, FieldMixin):
    roltype_omschrijving = models.CharField(_("ROLTYPE omschrijving"), max_length=100)

    class Meta:
        verbose_name = _("Process ROL")
        verbose_name_plural = _("Process ROLlen")
