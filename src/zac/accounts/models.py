import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from .constants import AccessRequestResult
from .datastructures import ZaaktypeCollection
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Use the built-in user model.
    """

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer."),
        error_messages={"unique": _("A user with that username already exists.")},
    )
    first_name = models.CharField(_("first name"), max_length=255, blank=True)
    last_name = models.CharField(_("last name"), max_length=255, blank=True)
    email = models.EmailField(_("email address"), blank=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    # custom permissions
    auth_profiles = models.ManyToManyField(
        "AuthorizationProfile",
        blank=True,
        through="UserAuthorizationProfile",
    )

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name


# Permissions


class AuthorizationProfile(models.Model):
    """
    Model a set of permission groups that can be assigned to a user.

    "Autorisatieprofiel" in Dutch. This is the finest-grained object that is exposed
    to external systems (via SCIM eventually). Towards IAM/SCIM, this maps to the
    Entitlement concept.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(_("naam"), max_length=255)
    permission_sets = models.ManyToManyField(
        "PermissionSet",
        verbose_name=_("permission sets"),
        help_text=_(
            "Selecting multiple sets makes them add/merge all the permissions together."
        ),
    )

    class Meta:
        verbose_name = _("authorization profile")
        verbose_name_plural = _("authorization profiles")

    def __str__(self):
        return self.name


class PermissionSet(models.Model):
    """
    A collection of permissions that belong to a zaaktype.
    """

    name = models.CharField(_("naam"), max_length=255, unique=True)
    description = models.TextField(_("description"), blank=True)
    permissions = ArrayField(
        models.CharField(max_length=255, blank=False),
        blank=True,
        default=list,
        verbose_name=_("permissions"),
    )
    catalogus = models.URLField(
        _("catalogus"),
        help_text=_("Zaaktypencatalogus waarin de zaaktypen voorkomen."),
        blank=True,
    )
    zaaktype_identificaties = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text=(
            "All permissions selected are scoped to these zaaktypen. "
            "If left empty, this applies to all zaaktypen."
        ),
    )
    max_va = models.CharField(
        _("maximale vertrouwelijkheidaanduiding"),
        max_length=100,
        choices=VertrouwelijkheidsAanduidingen.choices,
        default=VertrouwelijkheidsAanduidingen.openbaar,
        help_text=_(
            "Spans Zaken until and including this vertrouwelijkheidaanduiding."
        ),
    )
    informatieobjecttype_catalogus = models.URLField(
        verbose_name=_("informatieobjecttype catalogus"),
        help_text=_(
            "Informatieobjecttype catalogus waarin de informatieobjecttypen voorkomen."
        ),
        blank=True,
    )
    informatieobjecttype_omschrijvingen = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text=_(
            "Specifies which document types within the case can be viewed. "
            "If left empty, all documents in the case can be viewed."
        ),
        verbose_name=_("informatieobjecttype omschrijvingen"),
    )
    informatieobjecttype_max_va = models.CharField(
        verbose_name=_("informatieobjecttype maximum vertrouwelijkheidaanduiding"),
        max_length=100,
        choices=VertrouwelijkheidsAanduidingen.choices,
        default=VertrouwelijkheidsAanduidingen.openbaar,
        help_text=_(
            "Maximum level of confidentiality for the document types in the case."
        ),
    )

    class Meta:
        verbose_name = _("permission set")
        verbose_name_plural = _("permission sets")

    def __str__(self):
        return f"{self.name} ({self.get_max_va_display()})"

    def get_absolute_url(self):
        return reverse("accounts:permission-set-detail", args=[self.id])

    @cached_property
    def zaaktypen(self) -> ZaaktypeCollection:
        return ZaaktypeCollection(
            catalogus=self.catalogus, identificaties=self.zaaktype_identificaties
        )


class UserAuthorizationProfile(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    auth_profile = models.ForeignKey("AuthorizationProfile", on_delete=models.CASCADE)

    start = models.DateTimeField(_("start"), blank=True, null=True)
    end = models.DateTimeField(_("end"), blank=True, null=True)


class AccessRequest(models.Model):
    requester = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="initiated_requests"
    )
    handler = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="handled_requests",
        help_text=_("user who has handled the request"),
    )
    zaak = models.URLField(
        _("zaak"),
        max_length=1000,
        help_text=_("URL reference to the zaak in its API"),
    )
    comment = models.CharField(_("comment"), max_length=1000, blank=True)
    result = models.CharField(
        _("result"), max_length=50, choices=AccessRequestResult.choices, blank=True
    )
    start_date = models.DateField(_("start date"), blank=True, null=True)
    end_date = models.DateField(_("end date"), blank=True, null=True)

    def clean(self):
        super().clean()

        if self.result and not self.handler:
            raise ValidationError(
                _("The result can't be specified without it's handler")
            )
