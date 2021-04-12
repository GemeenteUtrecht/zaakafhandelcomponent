from typing import Any, Dict

from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.template import Library

from zac.accounts.models import AccessRequest
from zac.core.services import find_zaak

register = Library()


@register.inclusion_tag("includes/nav-menu__item.html", takes_context=True)
def nav_menu_item(
    context: dict, target: str, label: str, count: int = None, *args, **kwargs
) -> Dict[str, Any]:
    exact = kwargs.pop("exact", False)
    target_url = resolve_url(target, *args, **kwargs)

    request: HttpRequest = context.get("request")
    is_active = request and (
        request.path.startswith(target_url) if not exact else request.path == target_url
    )

    return {
        "label": label,
        "target_url": target_url,
        "is_active": is_active,
        "count": count,
    }


@register.simple_tag
def count_access_requests(**kwargs):
    """returns the number of active access requests for a zaak"""
    zaak = find_zaak(**kwargs)
    return AccessRequest.objects.filter(zaak=zaak.url, result="").count()


# Deprecated
# this tag is used only to support legacy SSR views
# Should be deletes after moving to SPA
@register.simple_tag
def has_perm(perm, user, obj=None):
    if not hasattr(user, "has_perm"):  # pragma: no cover
        return False  # swapped user model that doesn't support permissions
    else:
        return user.has_perm(perm, obj)
