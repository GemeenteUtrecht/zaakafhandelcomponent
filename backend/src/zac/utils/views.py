from django import http
from django.template import TemplateDoesNotExist, loader
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_403_TEMPLATE_NAME, ERROR_500_TEMPLATE_NAME

from zac.core.services import find_zaak


@requires_csrf_token
def server_error(request, template_name=ERROR_500_TEMPLATE_NAME):
    """
    500 error handler.

    Templates: :template:`500.html`
    Context: None
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_500_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return http.HttpResponseServerError(
            "<h1>Server Error (500)</h1>", content_type="text/html"
        )
    context = {"request": request}
    return http.HttpResponseServerError(template.render(context))


@requires_csrf_token
def permission_denied(request, exception, template_name=ERROR_403_TEMPLATE_NAME):
    """
    Permission denied (403) handler.

    Copy-paste of django default permission_denied view with context update with zaak behandelaars
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_403_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return http.HttpResponseForbidden(
            "<h1>403 Forbidden</h1>", content_type="text/html"
        )

    context = {"exception": str(exception), "can_request_access": False}

    if (
        request.resolver_match.url_name == "zaak-detail"
        and request.user.is_authenticated
    ):
        kwargs = request.resolver_match.kwargs
        zaak = find_zaak(**kwargs)
        has_requested_access = request.user.initiated_requests.filter(
            zaak=zaak.url
        ).exists()

        context.update(
            {
                "can_request_access": not has_requested_access,
                "has_requested_access": has_requested_access,
                "zaak_kwargs": kwargs,
            }
        )

    return http.HttpResponseForbidden(template.render(request=request, context=context))
