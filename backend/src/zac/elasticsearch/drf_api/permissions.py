from zac.accounts.permissions import Permission
from zac.api.permissions import SearchReportDefinitionPermission

from ..blueprints import SearchReportBlueprint

zoek_rapport_inzien = Permission(
    name="rapport:inzien",
    description="Laat toe om zoek rapporten in te zien.",
    blueprint_class=SearchReportBlueprint,
)


class CanDownloadSearchReports(SearchReportDefinitionPermission):
    permission = zoek_rapport_inzien
