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


def get_access_log_report(
    start_period: datetime,
    end_period: Optional[datetime] = None,
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
    # Make datetimes timezone-aware
    tz = get_default_timezone()
    start_dt = make_aware(datetime.combine(start_period, time.min), timezone=tz)
    end_dt = make_aware(datetime.combine(end_period, time.max), timezone=tz)

    # Aggregate login counts per username per day
    login_counts = (
        AccessLog.objects.filter(attempt_time__gte=start_dt, attempt_time__lte=end_dt)
        .values("username", day=TruncDate("attempt_time"))
        .annotate(logins=Count("id"))
        .order_by("username", "day")
    )

    all_dates_iso = [d.date().isoformat() for d in _daterange(start_period, end_period)]
    # Build: username -> { "YYYY-MM-DD": count, ... } and total counts
    user_day_logins: Dict[str, Dict[str, int]] = {}
    total_logins: Dict[str, int] = {}

    for entry in login_counts:
        username = entry["username"]
        day_iso = entry["day"].isoformat()
        count = entry["logins"]
        per_day = user_day_logins.setdefault(username, {})
        per_day[day_iso] = count
        total_logins[username] = total_logins.get(username, 0) + count

    usernames = sorted(user_day_logins.keys())
    if not usernames:
        return []  # No logins in the range

    # Single batch fetch of user metadata (avoids N+1)
    user_qs = User.objects.filter(username__in=usernames).only(
        "username", "first_name", "last_name", "email"
    )
    user_map = {u.username: (u.get_full_name() or "", u.email or "") for u in user_qs}

    result = []
    for username in usernames:
        full_name, email_addr = user_map.get(username, ("", ""))
        per_day = user_day_logins.get(username, {})

        # Fill missing days with 0
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
