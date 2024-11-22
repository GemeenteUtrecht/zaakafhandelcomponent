import csv
from datetime import date, datetime
from io import StringIO
from typing import List, Optional

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils.timezone import make_aware

from axes.models import AccessLog
from pytz import timezone

from zac.accounts.models import User

TZ = timezone("Europe/Amsterdam")


def send_access_log_email(
    recipient_list: List[str], start_date: date, end_date: Optional[date] = None
) -> None:
    logs = AccessLog.objects.filter(
        attempt_time__gte=make_aware(datetime.combine(start_date, datetime.min.time()))
    )
    if end_date:
        logs.filter(
            attempt_time__lte=make_aware(
                datetime.combine(end_date, datetime.max.time())
            )
        )

    user_logs = {}
    for log in logs:
        if log.username in user_logs:
            if log.attempt_time:
                user_logs[log.username]["login"].append(log.attempt_time.astimezone(TZ))
            if log.logout_time:
                user_logs[log.username]["logout"].append(log.logout_time.astimezone(TZ))
        else:
            user_logs[log.username] = {"login": [], "logout": []}
            if log.attempt_time:
                user_logs[log.username]["login"].append(log.attempt_time.astimezone(TZ))
            if log.logout_time:
                user_logs[log.username]["logout"].append(log.logout_time.astimezone(TZ))

    message = [["naam", "email", "gebruikersnaam", "login", "logout"]]
    for user, log in user_logs.items():
        user = User.objects.get(username=user)
        log["login"] = min(log["login"]) if log["login"] else "N/A"
        log["logout"] = max(log["logout"]) if log["logout"] else "N/A"
        line = [
            user.get_full_name(),
            user.email,
            user.username,
            log["login"],
            log["logout"],
        ]
        message.append(line)

    body = f"Er waren vandaag: {len(user_logs)} unieke gebruikers ingelogd. Zie bijlage voor een csv met details."
    email = EmailMessage(
        subject=f"{date.today().isoformat()} - gebruikerlogs zaakafhandelcomponent GU",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )

    with StringIO() as csv_file:
        csv_writer = csv.writer(csv_file)
        for line in message:
            csv_writer.writerow(line)
        email.attach(
            f"{date.today().isoformat()}-zac-gu-gebruikerlogs.csv",
            csv_file.getvalue(),
            "text/csv",
        )
        email.send(fail_silently=False)
    return None
