from django.db import models
from django.utils.translation import gettext as _
from solo.models import SingletonModel


class LandingPageConfiguration(SingletonModel):
    title = models.CharField(max_length=255, default=_("Startpagina Werkomgeving"))
    image = models.ImageField(help_text=_("Kies de afbeelding die bovenaan de pagina wordt getoond."), blank=True, null=True)

    def __str__(self) -> str:
        return self.title

    class Meta:
        verbose_name = _("Landingspagina configuratie")


class LandingPageSection(models.Model):
    name = models.CharField(max_length=25)
    icon = models.CharField(max_length=25)
    landing_page_configuration = models.ForeignKey(LandingPageConfiguration, on_delete=models.PROTECT, related_name="sections")

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = _("Landingspagina sectie")


class LandingPageLink(models.Model):
    label = models.CharField(max_length=25)
    icon = models.CharField(max_length=25, blank=True)
    href = models.CharField(max_length=255)
    landing_page_configuration = models.ForeignKey(LandingPageConfiguration, on_delete=models.PROTECT, related_name="links", blank=True, null=True)
    landing_page_section = models.ForeignKey(LandingPageSection, on_delete=models.PROTECT, related_name="links", blank=True, null=True)

    def __str__(self) -> str:
        return self.label

    class Meta:
        verbose_name = _("Landingspagina link")
