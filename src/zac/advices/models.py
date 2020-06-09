from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .constants import AdviceObjectTypes
from .query import AdviceQuerySet, DocumentAdviceQuerySet


class Advice(models.Model):
    """
    Model Advice which can be given on certain "documents".

    A document can be an actual document, or a Case as a unit. Advice is always given
    by a certain user.
    """

    # object identification
    object_url = models.URLField(
        _("object URL"),
        max_length=1000,
        help_text=_(
            "URL reference to the object in its API. Together with "
            "object_type, the object is understood."
        ),
    )
    object_type = models.CharField(
        _("object type"),
        choices=AdviceObjectTypes.choices,
        default=AdviceObjectTypes.document,
        max_length=20,
    )

    # advice contents
    advice = models.TextField(
        _("advice text"),
        blank=True,
        max_length=1000,
        help_text=_("The content of the advice"),
    )
    accord = models.BooleanField(
        _("accord"),
        default=False,
        help_text=_("Check to indicate you agree with the document(s)."),
    )

    # audit trail & history
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_("user"),
        help_text=_("User giving the advice"),
    )
    created = models.DateTimeField(_("created"), auto_now_add=True)

    objects = AdviceQuerySet.as_manager()

    class Meta:
        verbose_name = _("advice")
        verbose_name_plural = _("advices")

    def __str__(self):
        if not self.pk:
            return "Pending Advice"
        return f"{self.created.isoformat()} - {self.object_url}"


class DocumentAdvice(models.Model):
    """
    Record which version of a document contains suggestions for an earlier version.

    Users giving advice can choose to download the original document and upload an
    edited version of this document. The edited version can contain fixes or annotations
    with feedback.

    This model tracks:
    * which advice it's a part of
    * which particular document was updated
    * what the source version of the document was
    * what the new version is of this particular document
    """

    advice = models.ForeignKey("Advice", on_delete=models.CASCADE)
    document = models.URLField(
        _("document URL"),
        help_text=_(
            "URL reference to the source document in the Documents API. May "
            "include the 'versie' querystring parameter."
        ),
    )
    source_version = models.PositiveSmallIntegerField(_("source version"))
    advice_version = models.PositiveSmallIntegerField(_("advice version"))

    objects = DocumentAdviceQuerySet.as_manager()

    class Meta:
        verbose_name = _("document advice")
        verbose_name_plural = _("document advices")

    def __str__(self):
        return f"{self.source_version} -> {self.advice_version}"
