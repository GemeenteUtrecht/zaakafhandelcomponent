"""
Implement setting up the subscriptions.
"""
from typing import List
from urllib.parse import urljoin

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.authtoken.models import Token
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from .models import Subscription

User = get_user_model()


def subscribe_all(domain: str) -> List[Subscription]:
    user, _ = User.objects.get_or_create(username="notifications api")
    token, _ = Token.objects.get_or_create(user=user)

    subs = []
    for service in Service.objects.filter(api_type=APITypes.nrc):
        subs.append(subscribe(service, token.key, domain))
    return subs


def subscribe(service: Service, token: str, domain: str) -> Subscription:
    client = service.build_client()

    auth_value = f"Token {token}"
    url = urljoin(domain, reverse("notifications:callback"))

    _sub = client.create(
        "abonnement",
        {
            "callbackUrl": url,
            "auth": auth_value,
            "kanalen": [
                {
                    "naam": "zaken",
                    "filters": {},
                }
            ],
        },
    )

    subscription = Subscription.objects.create(url=_sub["url"])
    return subscription
