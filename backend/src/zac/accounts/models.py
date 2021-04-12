import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from elasticsearch_dsl.query import Query

from zac.utils.exceptions import get_error_list

from .constants import AccessRequestResult, PermissionObjectType
from .managers import UserManager
from .permissions import registry
from .query import (
    AccessRequestQuerySet,
    AtomicPermissionQuerySet,
    BlueprintPermissionQuerySet,
)


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
    atomic_permissions = models.ManyToManyField(
        "AtomicPermission",
        verbose_name=_("atomic permissions"),
        related_name="users",
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
    name = models.CharField(
        _("name"),
        max_length=255,
        help_text=_(
            "Use an easily recognizable name that maps to the function of users."
        ),
    )
    blueprint_permissions = models.ManyToManyField(
        "BlueprintPermission",
        verbose_name=_("blueprint permissions"),
        related_name="auth_profiles",
    )

    class Meta:
        verbose_name = _("authorization profile")
        verbose_name_plural = _("authorization profiles")

    def __str__(self):
        return self.name


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
    comment = models.CharField(
        _("comment"),
        max_length=1000,
        blank=True,
        help_text=_("Comment provided by the handler"),
    )
    result = models.CharField(
        _("result"),
        max_length=50,
        choices=AccessRequestResult.choices,
        blank=True,
        help_text=_("Result of the access request"),
    )
    start_date = models.DateField(
        _("start date"),
        blank=True,
        null=True,
        help_text=_("Start date of the granted access"),
    )
    end_date = models.DateField(
        _("end date"),
        blank=True,
        null=True,
        help_text=_("End date of the granted access"),
    )

    objects = AccessRequestQuerySet.as_manager()

    def clean(self):
        super().clean()

        if self.result and not self.handler:
            raise ValidationError(
                _("The result can't be specified without its handler")
            )


class AtomicPermission(models.Model):
    object_type = models.CharField(
        _("object type"),
        max_length=50,
        choices=PermissionObjectType.choices,
        help_text=_("Type of the objects this permission applies to"),
    )
    permission = models.CharField(
        _("Permission"), max_length=255, help_text=_("Name of the permission")
    )
    object_url = models.CharField(
        _("object URL"),
        max_length=1000,
        help_text=_("URL of the object in one of ZGW APIs this permission applies to"),
    )
    start_date = models.DateTimeField(
        _("start date"),
        default=timezone.now,
        help_text=_("Start date of the permission"),
    )
    end_date = models.DateTimeField(
        _("end date"),
        blank=True,
        null=True,
        help_text=_("End date of the permission"),
    )
    objects = AtomicPermissionQuerySet.as_manager()

    class Meta:
        verbose_name = _("permission definition")
        verbose_name_plural = _("permission definitions")

    def __str__(self):
        object_desc = self.object_url.split("/")[-1]
        return f"{self.permission} ({self.object_type} {object_desc})"


class BlueprintPermission(models.Model):
    object_type = models.CharField(
        _("object type"),
        max_length=50,
        choices=PermissionObjectType.choices,
        help_text=_("Type of the objects this permission applies to"),
    )
    permission = models.CharField(
        _("Permission"), max_length=255, help_text=_("Name of the permission")
    )
    policy = JSONField(
        _("policy"),
        help_text=_(
            "Blueprint permission definitions, used to check the access to objects based "
            "on their properties i.e. zaaktype, informatieobjecttype"
        ),
    )
    start_date = models.DateTimeField(
        _("start date"),
        default=timezone.now,
        help_text=_("Start date of the permission"),
    )
    end_date = models.DateTimeField(
        _("end date"),
        blank=True,
        null=True,
        help_text=_("End date of the permission"),
    )

    objects = BlueprintPermissionQuerySet.as_manager()

    class Meta:
        verbose_name = _("blueprint definition")
        verbose_name_plural = _("blueprint definitions")

    def __str__(self):
        return f"{self.permission} ({self.object_type})"

    def get_blueprint_class(self):
        permission = registry[self.permission]
        return permission.blueprint_class

    def clean(self):
        super().clean()

        # policy data should be validated against the serializer which is connected to this permission
        blueprint_class = self.get_blueprint_class()
        if self.policy:
            blueprint = blueprint_class(data=self.policy)
            if not blueprint.is_valid():
                raise ValidationError({"policy": get_error_list(blueprint.errors)})

    def has_access(self, obj, user=None) -> bool:
        blueprint_class = self.get_blueprint_class()
        blueprint = blueprint_class(self.policy, context={"user": user})
        return blueprint.has_access(obj)

    def get_search_query(self) -> Query:
        blueprint_class = self.get_blueprint_class()
        blueprint = blueprint_class(self.policy)
        return blueprint.search_query()
