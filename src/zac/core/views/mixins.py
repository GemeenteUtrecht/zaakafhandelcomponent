from typing import Optional

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.permissions import UserPermissions

from ..services import get_zaak


class TestZaakAccess:
    def check_zaak_access(self, url: str = "", zaak: Optional[Zaak] = None):
        """
        Check user permisisons for the zaak.

        :param url: fully qualified URL to the zaak, used to retrieve the object from
          the API to check the access.
        :param zaak: a Zaak instance, already retrieved from the API. zaak.zaaktype may
          be resolved into a ZaakType object, or be a string, in which case it must be
          a fully qualified zaaktype URL.
        :return: Zaak instance, either the passed in zaak, or the resolved object from
          the URL.
        :raises: PermissionDenied if the user does not have permission to access this
          zaak.
        """
        assert url or zaak, "Provide either URL to a zaak or a zaak object"

        user_perms = UserPermissions(self.request.user)
        if not zaak:
            zaak = get_zaak(zaak_url=url)

        # deal with unresolved relations...
        zaaktype = zaak.zaaktype
        if not isinstance(zaaktype, str):
            zaaktype = zaaktype.url

        if not user_perms.test_zaak_access(zaaktype, zaak.vertrouwelijkheidaanduiding):
            raise PermissionDenied(_("Insuffucient permissions to view this Zaak."))

        return zaak
