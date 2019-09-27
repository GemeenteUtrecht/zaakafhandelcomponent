from django import forms
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from zgw_consumers.admin_fields import get_zaaktypen


class ZaakTypeArrayField(ArrayField):
    def formfield(self, **kwargs):
        zaaktypen = get_zaaktypen()

        choices = [
            (
                f"Service: {service.label}",
                [
                    (
                        zaaktype["url"],
                        f"{zaaktype['identificatie']} - {zaaktype['omschrijving']}",
                    )
                    for zaaktype in _zaaktypen
                ],
            )
            for service, _zaaktypen in zaaktypen.items()
        ]

        defaults = {
            'form_class': forms.MultipleChoiceField,
            'choices': choices,
            'widget': forms.CheckboxSelectMultiple,
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)


class RegieZaakConfiguratie(models.Model):
    name = models.CharField(
        max_length=100,
        help_text=_("The name of the theme/subject")
    )
    zaaktype_main = models.URLField(
        _("Hoofdzaaktype"),
        help_text=_("Zaken van dit zaaktype worden als de regiezaak beschouwd.")
    )
    zaaktypes_related = ZaakTypeArrayField(
        base_field=models.URLField(),
        default=list,
        help_text=_("Zaken van deze zaaktypen worden beschouwd als onderdeel van de regiezaak."),
        blank=True,
    )

    class Meta:
        verbose_name = "regiezaak"
        verbose_name_plural = "regiezaken"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.zaaktype_main in self.zaaktypes_related:
            raise ValidationError(
                "'zaaktypes_related' can't include 'zaaktype_main'"
            )
