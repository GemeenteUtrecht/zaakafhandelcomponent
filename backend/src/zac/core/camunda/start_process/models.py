import uuid
from typing import Optional

from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.constants import RolTypes


class CamundaStartProcess(models.Model):
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

    def __str__(self):
        return self.process_definition_key


class CamundaStartProcessMixin(models.Model):
    camunda_start_process = models.ForeignKey(
        CamundaStartProcess,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class FieldLabelMixin(models.Model):
    label = models.CharField(
        _("label"), max_length=100, help_text=_("The label that will be shown.")
    )

    class Meta:
        abstract = True


class ProcessEigenschap(CamundaStartProcessMixin, FieldLabelMixin):
    eigenschapnaam = models.CharField(
        _("eigenschapnaam"),
        max_length=20,
        help_text=_("The name of the EIGENSCHAP"),
        unique=True,
    )
    default = models.CharField(
        _("default"),
        max_length=255,
        help_text=_("The default value of the ZAAKEIGENSCHAP."),
        blank=True,
        default="",
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


class ProcessEigenschapChoice(FieldLabelMixin):
    process_eigenschap = models.ForeignKey(
        ProcessEigenschap,
        on_delete=models.CASCADE,
    )
    value = models.CharField(
        _("value"),
        max_length=100,
        help_text=_("The value that will be used internally."),
    )

    class Meta:
        verbose_name = _("Process eigenschap choice")
        verbose_name_plural = _("Process eigenschap choices")


class ProcessInformatieObject(CamundaStartProcessMixin, FieldLabelMixin):
    informatieobjecttype_omschrijving = models.CharField(
        _("INFORMATIEOBJECTTYPE description"), max_length=100
    )
    allow_multiple = models.BooleanField(
        _("Allow multiple documents"),
        help_text=_(
            "A boolean flag to indicate whether a user is allowed to add more than 1 document."
        ),
        default=True,
    )

    class Meta:
        verbose_name = _("Process INFORMATIEOBJECT")
        verbose_name_plural = _("Process INFORMATIEOBJECTen")


class ProcessRol(CamundaStartProcessMixin, FieldLabelMixin):
    roltype_omschrijving = models.CharField(
        _("ROLTYPE omschrijving"),
        help_text=_("Description of ROLTYPE associated to ROL."),
        max_length=100,
    )
    betrokkene_type = models.CharField(
        _("betrokkene type"),
        choices=RolTypes,
        max_length=24,
        help_text=_("Betrokkene type of ROL."),
    )
    default = models.CharField(
        _("default"),
        max_length=255,
        blank=False,
        default="",
        help_text=_("A default value of the ROL betrokkene."),
    )

    class Meta:
        verbose_name = _("Process ROL")
        verbose_name_plural = _("Process ROLlen")
