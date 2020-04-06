import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

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
    entitlements = models.ManyToManyField(
        "Entitlement", blank=True, through="UserEntitlement",
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


class Entitlement(models.Model):
    """
    Model a set of permission groups that can be assigned to a user.

    "Autorisatieprofiel" in Dutch. This is the finest-grained object that is exposed
    to external systems (via SCIM eventually).
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
        verbose_name = _("entitlement")
        verbose_name_plural = _("entitlements")

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
        blank=False,
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

    class Meta:
        verbose_name = _("permission set")
        verbose_name_plural = _("permission sets")

    def __str__(self):
        return f"{self.name} ({self.get_max_va_display()})"


class UserEntitlement(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    entitlement = models.ForeignKey("Entitlement", on_delete=models.CASCADE)

    start = models.DateTimeField(_("start"), blank=True, null=True)
    end = models.DateTimeField(_("end"), blank=True, null=True)
