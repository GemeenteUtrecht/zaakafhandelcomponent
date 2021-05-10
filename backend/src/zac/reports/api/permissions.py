from zac.accounts.permissions import Permission
from zac.api.permissions import ReportDefinitionPermission

from ..blueprints import ReportBlueprint

rapport_inzien = Permission(
    name="rapport:inzien",
    description="Laat toe om rapporten in te zien.",
    blueprint_class=ReportBlueprint,
)


class CanDownloadReports(ReportDefinitionPermission):
    permission = rapport_inzien
