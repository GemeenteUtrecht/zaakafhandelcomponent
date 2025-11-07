"""
Implement setting up the subscriptions.
"""

from typing import List
from urllib.parse import urljoin

from django.urls import reverse_lazy

from rest_framework.authtoken.models import Token
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.models import User

from .models import Subscription

DESIRED = [
    {
        "path": reverse_lazy("notifications:callback"),
        "channel": "zaken",
        "filters": {},
    },
    {
        "path": reverse_lazy("notifications:callback"),
        "channel": "zaaktypen",
        "filters": {},
    },
    {
        "path": reverse_lazy("notifications:callback"),
        "channel": "informatieobjecttypen",
        "filters": {},
    },
    {
        "path": reverse_lazy("notifications:callback"),
        "channel": "documenten",
        "filters": {},
    },
    {
        "path": reverse_lazy("notifications:callback"),
        "channel": "objecten",
        "filters": {},
    },
]


def subscribe_all(domain: str) -> List[Subscription]:
    """
    Subscribe to the configured channels, on all known NRCs.

    Subscription is idempotent - the actual subscription will check if the desired
    subscription already exists and only create it if it doesn't yet.

    A system user/service account is created, whose token is used to authenticate
    against the ZAC API.

    :param domain: The domain (including protocol) where the application is hosted.
      Required to build fully qualified callback URLs.
    """
    user, _ = User.objects.get_or_create(username="notifications api")
    token, _ = Token.objects.get_or_create(user=user)

    subs = []
    for service in Service.objects.filter(api_type=APITypes.nrc):
        subs += subscribe(service, token.key, domain)
    return subs


def subscribe(service: Service, token: str, domain: str) -> List[Subscription]:
    nrc_client = service.build_client()

    auth_value = f"Token {token}"

    # fetch existing subs
    abonnementen = []
    for subscription in Subscription.objects.all():
        _client = Service.get_client(subscription.url)
        abonnementen.append(_client.retrieve("abonnement", url=subscription.url))

    to_create = []
    for desired_subscription in DESIRED:
        fully_qualified_url = urljoin(domain, str(desired_subscription["path"]))
        desired_subscription["callbackUrl"] = fully_qualified_url
        channel_definition = {
            "naam": desired_subscription["channel"],
            "filters": desired_subscription["filters"],
        }

        is_present = any(
            abo
            for abo in abonnementen
            if abo["callbackUrl"] == fully_qualified_url
            and channel_definition in abo["kanalen"]
        )
        if is_present:
            continue
        to_create.append(desired_subscription)

    new_subs = []
    for definition in to_create:
        _sub = nrc_client.create(
            "abonnement",
            {
                "callbackUrl": definition["callbackUrl"],
                "auth": auth_value,
                "kanalen": [
                    {
                        "naam": definition["channel"],
                        "filters": definition["filters"],
                    }
                ],
            },
        )

        subscription = Subscription.objects.create(url=_sub["url"])
        new_subs.append(subscription)

    return new_subs
