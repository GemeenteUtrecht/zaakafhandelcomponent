import rules

from zac.accounts.permissions import UserPermissions
from zac.core.services import get_zaaktypen

from .models import Report


@rules.predicate
def has_access_to_report_zaaktypen(user, report: Report):
    zaaktypen = get_zaaktypen(UserPermissions(user))
    identificaties = {zt.identificatie for zt in zaaktypen}
    return set(report.zaaktypen).issubset(identificaties)


rules.add_rule("reports:download", has_access_to_report_zaaktypen)
