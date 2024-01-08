import logging
from typing import Dict

from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes

logger = logging.getLogger(__name__)


class CoreConfig(SingletonModel):
    """
    A singleton model to configure core configuration of the ZAC.
    Without a properly configured CoreConfig, the ZAC will not function.

    Please refer to the configuration documentation for configuration.
    """

    primary_drc = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.drc},
        related_name="+",
    )
    primary_brc = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.brc},
        related_name="+",
    )
    primary_objects_api = models.ForeignKey(
        verbose_name=_("Primary OBJECTS API"),
        to="zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.orc},
        related_name="+",
        help_text=_("Default OBJECTS API service to use"),
    )
    primary_objecttypes_api = models.ForeignKey(
        verbose_name=_("Primary OBJECTTYPES API"),
        to="zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.orc},
        related_name="+",
        help_text=_("Default OBJECTTYPES API service to use"),
    )
    app_id = models.URLField(
        _("BPTL Application ID"),
        help_text=_(
            "A (globally) unique ID of the BPTL application. In this case the URL that points to the appropriate "
            "application on the Open Zaak Autorisaties API."
        ),
        default="",
    )
    non_adfs_login_enabled = models.BooleanField(
        _("Non-ADFS login enabled"),
        help_text=_("A flag that allows non-ADFS login (True) or not (False)."),
        default=True,
    )

    class Meta:
        verbose_name = _("global configuration")

    def __str__(self):
        return force_str(self._meta.verbose_name)


class MetaObjectTypesConfig(SingletonModel):
    """
    A singleton model that holds the URL-references of the meta objecttypes.
    `meta`-objecttypes are used to store and read data not supported by Open Zaak.

    Please refer to the Meta ObjectTypes documentation for further information.

    """

    default = models.BooleanField(
        default=True,
        help_text=_(
            "Setting to False will allow the user to define custom objecttypes instead of the URL-references retrieved from the list of meta objecttypes from the OBJECTS API."
        ),
    )

    meta_list_objecttype = models.URLField(
        _("URL-reference to MetaListObjectType in OBJECTTYPES API."),
        help_text=_(
            "A URL-reference to the Meta List OBJECTTYPE. This is used to fetch the meta list objecttype for managing meta objects and objecttypes."
        ),
        default="",
    )

    checklist_objecttype = models.URLField(
        _("URL-reference to Checklist in OBJECTTYPES API."),
        help_text=_(
            "A URL-reference to the Checklist OBJECTTYPE. This is used to fetch the checklist objecttype for a ZAAK."
        ),
        default="",
    )
    checklisttype_objecttype = models.URLField(
        _("URL-reference to ChecklistType in OBJECTTYPES API."),
        help_text=_(
            "A URL-reference to the ChecklistType OBJECTTYPE. This is used to get the questions for a checklist for a ZAAKTYPE."
        ),
        default="",
    )
    oudbehandelaren_objecttype = models.URLField(
        _("URL-reference to Oudbehandelaren in OBJECTTYPES API."),
        help_text=_(
            "A URL-reference to the Oudbehandelaren OBJECTTYPE. This is used to register the old ROL when the ROL was of ROLTYPE `behandelaar`."
        ),
        default="",
    )
    start_camunda_process_form_objecttype = models.URLField(
        _("URL-reference to StartCamundaForms in OBJECTTYPES API."),
        help_text=_(
            "A URL-reference to the StartCamundaForms OBJECTTYPE. This is used to set the right variables for the camunda process related to the ZAAKTYPE."
        ),
        default="",
    )
    zaaktype_attribute_objecttype = models.URLField(
        _("URL-reference to ZaaktypeAttributes in OBJECTTYPES API."),
        help_text=_(
            "A URL-reference to the ZaaktypeAttributes OBJECTTYPE. This is used to get extra data for EIGENSCHAPs."
        ),
        default="",
    )

    class Meta:
        verbose_name = _("meta objecttype configuration")

    def __str__(self):
        return force_str(self._meta.verbose_name)

    def save(self, *args, **kwargs):
        if self.default and self.meta_list_objecttype:
            from zac.core.services import search_objects

            response, qp = search_objects({"type": self.meta_list_objecttype})
            if response["count"] == 1:
                urls = response["results"][0]["record"]["data"].get(
                    "metalistobjecttypes", dict()
                )
            else:
                logger.warning(
                    "meta_list_object should be unique. Grabbing the first one."
                )

            for objecttype_name, url in urls.items():
                if url:
                    setattr(self, objecttype_name, url)
        return super().save(*args, **kwargs)

    @property
    def meta_objecttype_urls(self) -> Dict[str, str]:
        return {
            field.get_attname(): getattr(self, field.name)
            for field in self._meta.get_fields()
            if isinstance(field, models.URLField)
        }
