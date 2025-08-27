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

    # 1) Aggregate login counts per username per *local calendar day*
    #    Use annotate(...) first, then values(...) for best cross-DB behavior.
    login_counts = (
        AccessLog.objects.filter(attempt_time__gte=start_dt, attempt_time__lte=end_dt)
        .annotate(day=TruncDate("attempt_time", tzinfo=tz))
        .values("username", "day")
        .annotate(logins=Count("id"))
        .order_by("username", "day")
    )

    # 2) Build the full date range as *date objects*
    all_days: List[date] = list(_daterange(start_period, end_period))

    # username -> { date: count }
    user_day_logins: Dict[str, Dict[date, int]] = {}
    total_logins: Dict[str, int] = {}

    for entry in login_counts:
        username = entry["username"]
        day_val = entry["day"]

        # Normalize DB value to a Python date
        if isinstance(day_val, datetime):
            day_key = day_val.date()
        elif isinstance(day_val, date):
            day_key = day_val
        else:
            # Fallback parse (rare)
            s = str(day_val).replace("Z", "+00:00")
            try:
                day_key = datetime.fromisoformat(s).date()
            except Exception:
                day_key = datetime.strptime(
                    str(day_val).split("T", 1)[0], "%Y-%m-%d"
                ).date()

        count = int(entry["logins"])
        per_day = user_day_logins.setdefault(username, {})
        per_day[day_key] = count
        total_logins[username] = total_logins.get(username, 0) + count

    usernames = sorted(user_day_logins.keys())
    if not usernames:
        return []  # No logins in the range

    # 3) Single batch fetch of user metadata (avoids N+1)
    user_qs = User.objects.filter(username__in=usernames).only(
        "username", "first_name", "last_name", "email"
    )
    user_map = {u.username: (u.get_full_name() or "", u.email or "") for u in user_qs}

    # 4) Build result, converting date keys to 'YYYY-MM-DD' at the last moment
    result: List[Dict] = []
    for username in usernames:
        full_name, email_addr = user_map.get(username, ("", ""))
        per_day = user_day_logins.get(username, {})

        logins_per_day = {d.isoformat(): per_day.get(d, 0) for d in all_days}

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
