import binascii
import os
import uuid
from datetime import date, datetime
from hashlib import blake2b
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, Group, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import JSONField, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from elasticsearch_dsl.query import Query

from zac.utils.exceptions import get_error_list

from .constants import (
    AccessRequestResult,
    PermissionObjectTypeChoices,
    PermissionReason,
)
from .managers import UserManager
from .permissions import object_type_registry
from .query import (
    AccessRequestQuerySet,
    AtomicPermissionQuerySet,
    BlueprintPermissionQuerySet,
    UserAtomicPermissionQuerySet,
)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Extend the built-in user model with handy fields related to history, permissions and groups.
    """

    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    email = models.EmailField(_("email address"), blank=True)
    first_name = models.CharField(_("first name"), max_length=255, blank=True)
    last_name = models.CharField(_("last name"), max_length=255, blank=True)
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    recently_viewed = models.JSONField(
        _("recently viewed ZAAKs"),
        default=list,
        blank=True,
        help_text=_("A list of recently viewed ZAAKs."),
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer."),
        error_messages={"unique": _("A user with that `username` already exists.")},
    )

    # custom permissions
    atomic_permissions = models.ManyToManyField(
        "AtomicPermission",
        blank=True,
        verbose_name=_("atomic permissions"),
        related_name="users",
        through="UserAtomicPermission",
    )
    auth_profiles = models.ManyToManyField(
        "AuthorizationProfile",
        blank=True,
        through="UserAuthorizationProfile",
    )

    # Group management
    manages_groups = models.ManyToManyField(
        Group,
        blank=True,
        verbose_name=_("manages groups"),
        related_name="manager",
    )

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.UniqueConstraint(
                fields=["email"], condition=~Q(email=""), name="filled_email_unique"
            )
        ]

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip() or self.username

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def has_pending_access_request(self, zaak) -> bool:
        return self.initiated_requests.actual().filter(zaak=zaak.url, result="")


# Permissions
class AuthorizationProfile(models.Model):
    """
    Model a set of permission groups that can be assigned to a user.

    "Autorisatieprofiel" in Dutch. This is the finest-grained object that is exposed
    to external systems.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(
        _("name"),
        max_length=255,
        help_text=_(
            "Use an easily recognizable name that maps to the function of users that's unique."
        ),
        unique=True,
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
    """
    User authorization profiles serve to relate a user to an authorization profile from a start to end date.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    auth_profile = models.ForeignKey("AuthorizationProfile", on_delete=models.CASCADE)

    start = models.DateTimeField(_("start"), default=timezone.now)
    end = models.DateTimeField(
        _("end"), default=timezone.make_aware(datetime(2999, 12, 31))
    )
    is_active = models.BooleanField(_("is active"), default=True)

    class Meta:
        verbose_name = _("user-authorization profile")
        verbose_name_plural = _("user-authorization profiles")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "auth_profile", "is_active"],
                condition=Q(is_active=True),
                name="unique_active_userauthorizationprofiles",
            )
        ]

    def clean(self, id=Optional[int]):
        super().clean()
        if (
            not id
            and UserAuthorizationProfile.objects.filter(
                user=self.user,
                auth_profile=self.auth_profile,
                is_active=True,
            ).exists()
        ):
            raise ValidationError(
                "User already has an active authorization profile, please deactivate first."
            )

    def save(self, *args, **kwargs):
        self.clean(id=self.id if hasattr(self, "id") else None)
        return super().save(*args, **kwargs)


class AccessRequest(models.Model):
    """
    Access requests serve to grant users specific permissions for a ZAAK when they request them.
    A handler must have the permissions to handle access requests but also the permissions requested.
    """

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="initiated_requests",
    )
    handler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="handled_requests",
        help_text=_("user who has handled the request"),
    )
    zaak = models.URLField(
        _("zaak"),
        max_length=1000,
        help_text=_("URL-reference to the ZAAK in its API"),
    )
    comment = models.CharField(
        _("comment"),
        max_length=1000,
        blank=True,
        help_text=_("Comment provided by the requester"),
    )
    result = models.CharField(
        _("result"),
        max_length=50,
        choices=AccessRequestResult.choices,
        blank=True,
        help_text=_("Result of the access request"),
    )
    requested_date = models.DateField(
        _("requested date"),
        default=date.today,
        help_text=_("Date when the access request was created"),
    )
    handled_date = models.DateField(
        _("end date"),
        blank=True,
        null=True,
        help_text=_("Date when the access request was handled"),
    )

    objects = AccessRequestQuerySet.as_manager()

    def clean(self):
        super().clean()

        if self.result and not self.handler:
            raise ValidationError(
                _("The result can't be specified without its handler")
            )


class AtomicPermission(models.Model):
    """
    Permissions can be granted to specific objects. This is an `atomic permission`.
    Objects that currently are supported are:

        * `zaak`
        * `document`
    """

    object_type = models.CharField(
        _("object type"),
        max_length=50,
        choices=PermissionObjectTypeChoices.choices,
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

    objects = AtomicPermissionQuerySet.as_manager()

    class Meta:
        verbose_name = _("atomic permission")
        verbose_name_plural = _("atomic permissions")
        unique_together = ("permission", "object_url")

    @property
    def object_uuid(self):
        return self.object_url.rstrip("/").split("/")[-1]

    def __str__(self):
        return f"{self.permission} ({self.object_type} {self.object_uuid})"


class UserAtomicPermission(models.Model):
    """
    User atomic permissions serve to relate a user to an atomic permission from a start to end date.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    atomic_permission = models.ForeignKey("AtomicPermission", on_delete=models.CASCADE)
    access_request = models.ForeignKey(
        "AccessRequest",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        help_text=_("Access request that created this permission."),
    )
    reason = models.CharField(
        _("reason"),
        choices=PermissionReason.choices,
        max_length=50,
        blank=True,
        help_text=_("The reason why the permission was granted to the user"),
    )
    comment = models.CharField(
        _("comment"),
        max_length=1000,
        blank=True,
        help_text=_("Comment provided by the granter of the permission"),
    )
    start_date = models.DateTimeField(
        _("start date"),
        default=timezone.now,
        help_text=_("Start date of the permission"),
    )
    end_date = models.DateTimeField(
        _("end date"), blank=True, null=True, help_text=_("End date of the permission")
    )

    objects = UserAtomicPermissionQuerySet.as_manager()

    class Meta:
        db_table = "accounts_user_atomic_permissions"


class BlueprintPermission(models.Model):
    """
    Blueprint permissions are related to authorization profiles. They are together with the `role` the key
    that checks if the policy related to the blueprint permission which is related to the authorization profile
    is sufficient to grant access.
    """

    hashkey = models.CharField(
        max_length=32, blank=True, null=True, unique=True
    )  # short key for inter env migration purposes, set in self.save()
    object_type = models.CharField(
        _("object type"),
        max_length=50,
        choices=PermissionObjectTypeChoices.choices,
        help_text=_("Type of the objects this permission applies to"),
    )
    role = models.ForeignKey(
        "Role", on_delete=models.CASCADE, related_name="blueprint_permissions"
    )
    policy = JSONField(
        _("policy"),
        help_text=_(
            "Blueprint permission definitions, used to check the access to objects based "
            "on their properties i.e. ZAAKTYPE, INFORMATIEOBJECTTYPE"
        ),
    )

    objects = BlueprintPermissionQuerySet.as_manager()

    class Meta:
        verbose_name = _("blueprint permission")
        verbose_name_plural = _("blueprint permissions")
        ordering = ("role", "object_type", "policy__zaaktype_omschrijving")
        unique_together = ("role", "policy", "object_type")

    def __str__(self):
        if not self.policy:
            return f"{self.role}"

        blueprint_class = self.get_blueprint_class()
        blueprint = blueprint_class(self.policy)
        return f"{self.role}: {blueprint.short_display()}"

    def get_blueprint_class(self):
        object_type = object_type_registry[self.object_type]
        return object_type.blueprint_class

    def clean(self):
        super().clean()

        # policy data should be validated against the serializer which is connected to this permission
        blueprint_class = self.get_blueprint_class()
        if self.policy:
            blueprint = blueprint_class(data=self.policy)
            if not blueprint.is_valid():
                raise ValidationError({"policy": get_error_list(blueprint.errors)})

    def save(self, *args, **kwargs):
        h = blake2b(digest_size=16, usedforsecurity=False)
        h.update(f"{self.object_type}{self.role.name}{str(self.policy)}".encode())
        self.hashkey = h.hexdigest()
        return super().save(*args, **kwargs)

    def has_access(self, obj, user=None, permission=None) -> bool:
        blueprint_class = self.get_blueprint_class()
        blueprint = blueprint_class(self.policy, context={"user": user})
        return blueprint.has_access(obj, permission)

    def get_search_query(self, on_nested_field: Optional[str] = "") -> Query:
        blueprint_class = self.get_blueprint_class()
        blueprint = blueprint_class(self.policy)
        return blueprint.search_query(on_nested_field=on_nested_field)


class Role(models.Model):
    """
    A role comprises of a series of permissions and is related to the authorization profile.
    The permissions are used to check if a user can perform an action such as reading a ZAAK or DOCUMENT.
    """

    name = models.CharField(
        _("name"), max_length=100, unique=True, help_text=_("Name of the role")
    )
    permissions = ArrayField(
        models.CharField(_("permission"), max_length=255),
        help_text=_("List of the permissions"),
        default=list,
    )

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")

    def __str__(self):
        return self.name


class ApplicationToken(models.Model):
    """
    An application token can be granted to consumer of the ZAC REST APIs. They can be related to
    an authorization profile to finely control the access the consumer has to exposed ZAC REST APIs.
    """

    token = models.CharField(_("token"), max_length=40, primary_key=True)
    contact_person = models.CharField(
        _("contact person"),
        max_length=200,
        help_text=_("Name of the person in the organization who can access the API"),
    )
    email = models.EmailField(
        _("email"), help_text=_("Email of the person, who can access the API")
    )
    organization = models.CharField(
        _("organization"),
        max_length=200,
        blank=True,
        help_text=_("Organization which has access to the API"),
    )
    last_modified = models.DateTimeField(
        _("last modified"),
        auto_now=True,
        help_text=_("Last date when the token was modified"),
    )
    created = models.DateTimeField(
        _("created"), auto_now_add=True, help_text=_("Date when the token was created")
    )
    application = models.CharField(
        _("application"),
        max_length=200,
        blank=True,
        help_text=_("Application which has access to the API"),
    )
    administration = models.CharField(
        _("administration"),
        max_length=200,
        blank=True,
        help_text=_("Administration which has access to the API"),
    )

    # custom permissions
    auth_profiles = models.ManyToManyField(
        "AuthorizationProfile",
        blank=True,
        through="ApplicationTokenAuthorizationProfile",
    )
    has_all_reading_rights = models.BooleanField(
        _("has all reading rights"), default=False
    )

    class Meta:
        verbose_name = _("application token authorization")
        verbose_name_plural = _("application token authorizations")

    def __str__(self):
        return self.contact_person

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        return super().save(*args, **kwargs)

    def generate_token(self):
        return binascii.hexlify(os.urandom(20)).decode()


class ApplicationTokenAuthorizationProfile(models.Model):
    """
    Application token authorization profiles serve to relate an application token to an authorization profile from a start to end date.
    """

    application = models.ForeignKey("ApplicationToken", on_delete=models.CASCADE)
    auth_profile = models.ForeignKey("AuthorizationProfile", on_delete=models.CASCADE)

    start = models.DateTimeField(_("start"), default=timezone.now)
    end = models.DateTimeField(_("end"), blank=True, null=True)
