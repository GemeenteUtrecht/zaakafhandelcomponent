from django.db import models
from django.utils.translation import gettext_lazy as _


class OrganisatieOnderdeel(models.Model):
    """
    A model that saves the names and `slugs` of "organisatie-onderdelen".
    Currently not used.
    """

    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(_("slug"), max_length=24, unique=True)

    class Meta:
        verbose_name = _("organisatie-onderdeel")
        verbose_name_plural = _("organisatie-onderdelen")

    def __str__(self):
        return self.name
