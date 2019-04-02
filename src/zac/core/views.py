from django.core.cache import cache
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from .forms import ZakenFilterForm
from .services import get_zaaktypes, get_zaken


class Index(TemplateView):
    """
    Display the landing screen.
    """
    template_name = 'core/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['filter_form'] = ZakenFilterForm(
            data=self.request.GET if self.request.GET else None,
            initial={
                'zaaktypen': [zt.id for zt in get_zaaktypes()],
            }
        )

        context['zaken'] = get_zaken()
        return context


class FlushCacheView(View):

    def post(self, request, *args, **kwargs):
        referer = request.META['HTTP_REFERER']
        cache.clear()
        return redirect(referer)
