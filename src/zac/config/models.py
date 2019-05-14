import uuid

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from zds_client import Client, ClientAuth


class APITypes(DjangoChoices):
    zrc = ChoiceItem('zrc', _("ZRC"))
    ztc = ChoiceItem('ztc', _("ZTC"))
    drc = ChoiceItem('drc', _("DRC"))
    brc = ChoiceItem('brc', _("BRC"))


class Service(models.Model):
    label = models.CharField(_("label"), max_length=100)
    api_type = models.CharField(_("type"), max_length=20, choices=APITypes.choices)
    api_root = models.CharField(_("api root url"), max_length=255, unique=True)

    extra = JSONField(
        _("extra configuration"), default=dict,
        help_text=_("Extra configuration that's service-specific")
    )

    # credentials for the API
    client_id = models.CharField(max_length=255, blank=True)
    secret = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = _("service")
        verbose_name_plural = _("services")

    def __str__(self):
        return f"[{self.get_api_type_display()}] {self.label}"

    def save(self, *args, **kwargs):
        if not self.api_root.endswith('/'):
            self.api_root = f"{self.api_root}/"
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.api_type == APITypes.ztc:
            main_catalogus_uuid = self.extra.get('main_catalogus_uuid')
            if main_catalogus_uuid is None:
                raise ValidationError({
                    'extra': _("Expected a 'main_catalogus_uuid' extra config")
                })

            try:
                uuid.UUID(main_catalogus_uuid)
            except ValueError:
                raise ValidationError({
                    'extra': _("'main_catalogus_uuid' does not look like a valid UUID4"),
                })

    def build_client(self, **claims) -> Client:
        """
        Build an API client from the service configuration.
        """
        _uuid = uuid.uuid4()
        dummy_detail_url = f"{self.api_root}dummy/{_uuid}"
        client = Client.from_url(dummy_detail_url)
        client.auth = ClientAuth(client_id=self.client_id, secret=self.secret, **claims)
        return client
