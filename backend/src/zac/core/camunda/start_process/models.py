import uuid
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from ordered_model.models import OrderedModel
from zgw_consumers.api_models.catalogi import (
    Eigenschap,
    InformatieObjectType,
    RolType,
    ZaakType,
)
from zgw_consumers.api_models.constants import RolTypes

from zac.core.services import (
    get_eigenschappen,
    get_informatieobjecttypen_for_zaaktype,
    get_roltypen,
    get_zaaktypen,
)


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

    @property
    def zaaktype(self) -> ZaakType:
        return get_zaaktypen(
            catalogus=self.zaaktype_catalogus, identificatie=self.zaaktype_identificatie
        )[0]

    @property
    def roltypen(self) -> List[RolType]:
        return get_roltypen(self.zaaktype)

    @property
    def eigenschappen(self) -> List[Eigenschap]:
        return get_eigenschappen(self.zaaktype)

    @property
    def informatieobjecttypen(self) -> List[InformatieObjectType]:
        return get_informatieobjecttypen_for_zaaktype(self.zaaktype)


class CamundaStartProcessMixin(models.Model):
    camunda_start_process = models.ForeignKey(
        CamundaStartProcess,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class FieldLabelMixin(models.Model):
    label = models.CharField(
        _("label"),
        max_length=100,
        help_text=_("The label that will be shown."),
        default="",
    )

    class Meta:
        abstract = True


class RequiredMixin(models.Model):
    required = models.BooleanField(
        _("required"),
        help_text=_("A boolean flag to indicate if a value is required."),
        default=False,
    )

    class Meta:
        abstract = True


class MultipleChoiceMixin(models.Model):
    class Meta:
        abstract = True

    def get_choices(self):
        raise NotImplementedError("This method must be implemented by a subclass")

    @property
    def is_multiple_choice(self) -> bool:
        return self.get_choices().exists()

    @property
    def choices(self) -> Optional[QuerySet]:
        if choices := self.get_choices().values_list("label", "value"):
            return choices
        return None

    @property
    def valid_choice_values(self) -> Optional[QuerySet]:
        if valid_choices := self.get_choices().values_list("value", flat=True):
            return valid_choices
        return None


class OrderedMixin(OrderedModel):
    order_with_respect_to = "camunda_start_process"

    class Meta:
        abstract = True


class ProcessEigenschap(
    FieldLabelMixin,
    RequiredMixin,
    CamundaStartProcessMixin,
    OrderedMixin,
    models.Model,
):
    eigenschapnaam = models.CharField(
        _("eigenschapnaam"),
        max_length=20,
        help_text=_("The name of the EIGENSCHAP"),
        blank=True,
    )
    default = models.CharField(
        _("default"),
        max_length=255,
        help_text=_("The default value of the ZAAKEIGENSCHAP."),
        blank=True,
    )

    class Meta:
        verbose_name = _("Process EIGENSCHAP")
        verbose_name_plural = _("Process EIGENSCHAPpen")
        unique_together = (("camunda_start_process", "eigenschapnaam"),)

    def clean(self):
        super().clean()
        if self.eigenschapnaam not in [
            ei.naam for ei in self.camunda_start_process.eigenschappen
        ]:
            raise ValidationError(
                _(
                    "`{eigenschapnaam}` not found in the EIGENSCHAPpen from the ZAAKTYPE of camunda start process.".format(
                        eigenschapnaam=self.eigenschapnaam
                    )
                )
            )


class ProcessInformatieObject(
    FieldLabelMixin, RequiredMixin, CamundaStartProcessMixin, OrderedMixin, models.Model
):
    informatieobjecttype_omschrijving = models.CharField(
        _("INFORMATIEOBJECTTYPE description"),
        max_length=100,
        blank=True,
    )
    allow_multiple = models.BooleanField(
        _("Allow multiple documents"),
        help_text=_(
            "A boolean flag to indicate whether a user is allowed to add more than 1 document."
        ),
        default=False,
    )

    class Meta:
        verbose_name = _("Process INFORMATIEOBJECT")
        verbose_name_plural = _("Process INFORMATIEOBJECTen")

    def clean(self):
        super().clean()
        if self.informatieobjecttype_omschrijving not in [
            iot.omschrijving for iot in self.camunda_start_process.informatieobjecttypen
        ]:
            raise ValidationError(
                _(
                    "`{omschrijving}` not found in the INFORMATIEOBJECTTYPEs related to the ZAAKTYPE of camunda start process.".format(
                        omschrijving=self.informatieobjecttype_omschrijving
                    )
                )
            )


class ProcessRol(
    FieldLabelMixin,
    RequiredMixin,
    CamundaStartProcessMixin,
    OrderedMixin,
    models.Model,
):
    roltype_omschrijving = models.CharField(
        _("ROLTYPE omschrijving"),
        help_text=_("Description of ROLTYPE associated to ROL."),
        max_length=100,
        blank=True,
    )
    betrokkene_type = models.CharField(
        _("betrokkene type"),
        choices=RolTypes,
        max_length=24,
        help_text=_("Betrokkene type of ROL."),
    )

    class Meta:
        verbose_name = _("Process ROL")
        verbose_name_plural = _("Process ROLlen")

    def clean(self):
        super().clean()
        if self.roltype_omschrijving not in [
            iot.omschrijving for iot in self.camunda_start_process.roltypen
        ]:
            raise ValidationError(
                _(
                    "`{omschrijving}` not found in the ROLTYPEs of ZAAKTYPE of camunda start process.".format(
                        omschrijving=self.roltype_omschrijving
                    )
                )
            )
