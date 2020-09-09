from typing import Any, Dict

from zac.accounts.mixins import PermissionRequiredMixin

from ..base_views import BaseDetailView
from ..permissions import zaken_inzien
from ..services import find_zaak, get_besluiten


class ZaakBesluitenView(PermissionRequiredMixin, BaseDetailView):
    template_name = "core/zaak_besluiten.html"
    context_object_name = "zaak"
    permission_required = zaken_inzien.name

    def get_object(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "besluiten": get_besluiten(self.object),
            }
        )
        return context
