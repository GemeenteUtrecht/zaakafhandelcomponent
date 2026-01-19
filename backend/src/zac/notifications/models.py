from django.db import models
from django.utils.translation import gettext_lazy as _


class Subscription(models.Model):
    """
    A singleton model that holds the URL of the registered notification subscription.
    """

    url = models.URLField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Registered subscription")
        verbose_name_plural = _("Registered subscriptions")

    def __str__(self):
        return self.url
