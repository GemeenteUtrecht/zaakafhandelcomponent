from datetime import date, datetime, time, timedelta
from typing import Dict, Iterable, List, Optional

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils.timezone import get_default_timezone, make_aware

from axes.models import AccessLog

from zac.accounts.models import User


def _daterange(start: date, end: date) -> Iterable[date]:
    """Yield each date from start to end inclusive."""
    days = (end - start).days
    for n in range(days + 1):
        yield start + timedelta(days=n)


def _to_date_key(v) -> str:
    """Normalize a value (date/datetime/iso string) to 'YYYY-MM-DD'."""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v)
    try:
        # handle possible trailing 'Z'
        s2 = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s2).date().isoformat()
    except Exception:
        # crude fallback: split at 'T'
        return s.split("T", 1)[0]


def get_access_log_report(
    start_period: date,
    end_period: Optional[date] = None,
) -> List[Dict]:
    """
    Build an access-log report between start_period and end_period (inclusive).
    Returns a list of dicts with:
      - naam
      - email
      - gebruikersnaam
      - total_logins
      - logins_per_day (per-day counts across the range, zero-filled)
    """
    end_period = end_period or start_period

    tz = get_default_timezone()
    start_dt = make_aware(datetime.combine(start_period, time.min), timezone=tz)
    end_dt = make_aware(datetime.combine(end_period, time.max), timezone=tz)

    # Aggregate login counts per username per local *date*
    login_counts = (
        AccessLog.objects.filter(attempt_time__gte=start_dt, attempt_time__lte=end_dt)
        .values(
            "username", day=TruncDate("attempt_time", tzinfo=tz)
        )  # ensure local day
        .annotate(logins=Count("id"))
        .order_by("username", "day")
    )

    # Build the full date range keys as 'YYYY-MM-DD'
    all_dates_iso = [d.isoformat() for d in _daterange(start_period, end_period)]

    # username -> { 'YYYY-MM-DD': count }
    user_day_logins: Dict[str, Dict[str, int]] = {}
    total_logins: Dict[str, int] = {}

    for entry in login_counts:
        username = entry["username"]
        day_key = _to_date_key(entry["day"])  # normalize to 'YYYY-MM-DD'
        count = int(entry["logins"])
        per_day = user_day_logins.setdefault(username, {})
        per_day[day_key] = count
        total_logins[username] = total_logins.get(username, 0) + count

    usernames = sorted(user_day_logins.keys())
    if not usernames:
        return []  # No logins in the range

    # Single batch fetch of user metadata (avoids N+1)
    user_qs = User.objects.filter(username__in=usernames).only(
        "username", "first_name", "last_name", "email"
    )
    user_map = {u.username: (u.get_full_name() or "", u.email or "") for u in user_qs}

    result: List[Dict] = []
    for username in usernames:
        full_name, email_addr = user_map.get(username, ("", ""))
        per_day = user_day_logins.get(username, {})

        # Fill missing days with 0, keys are 'YYYY-MM-DD'
        logins_per_day = {d: per_day.get(d, 0) for d in all_dates_iso}

        result.append(
            {
                "naam": full_name,
                "email": email_addr,
                "gebruikersnaam": username,
                "total_logins": total_logins.get(username, 0),
                "logins_per_day": logins_per_day,
            }
        )

    return result
