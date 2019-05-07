from django.core.cache import cache
from django.shortcuts import redirect
from django.views import View

from .base_views import BaseDetailView, BaseListView
from .forms import ZakenFilterForm
from .services import find_zaak, get_zaaktypes, get_zaken


class Index(BaseListView):
    """
    Display the landing screen.
    """
    template_name = 'core/index.html'
    context_object_name = 'zaken'
    filter_form_class = ZakenFilterForm

    def get_object_list(self):
        filter_form = self.get_filter_form()
        filters = {}
        if filter_form.is_valid():
            filters['zaaktypes'] = filter_form.cleaned_data['zaaktypen']
        return get_zaken(**filters)

    def get_filter_form_initial(self):
        return {
            'zaaktypen': [zt.id for zt in get_zaaktypes()],
        }


class ZaakDetail(BaseDetailView):
    template_name = 'core/zaak_detail.html'
    context_object_name = 'zaak'

    def get_object(self):
        return find_zaak(**self.kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class FlushCacheView(View):

    def post(self, request, *args, **kwargs):
        referer = request.META['HTTP_REFERER']
        cache.clear()
        return redirect(referer)
