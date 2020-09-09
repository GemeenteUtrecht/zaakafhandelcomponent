from zac.accounts.mixins import PermissionRequiredMixin

from ..base_views import BaseDetailView
from ..permissions import zaken_inzien
from ..services import find_zaak


class ZaakBesluitenView(PermissionRequiredMixin, BaseDetailView):
    template_name = "core/zaak_besluiten.html"
    context_object_name = "zaak"
    permission_required = zaken_inzien.name

    def get_object(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak
