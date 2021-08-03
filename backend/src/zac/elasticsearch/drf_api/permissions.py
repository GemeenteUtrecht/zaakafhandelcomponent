from dataclasses import dataclass

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.permissions import Permission
from zac.api.permissions import SearchReportDefinitionPermission


@dataclass(frozen=True)
class SearchReportPermission(Permission):
    object_type: str = PermissionObjectTypeChoices.search_report


zoek_rapport_inzien = SearchReportPermission(
    name="rapport:inzien",
    description="Laat toe om zoek rapporten in te zien.",
)


class CanDownloadSearchReports(SearchReportDefinitionPermission):
    permission = zoek_rapport_inzien
