from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest
from django.views.generic import TemplateView

from ..search import REGISTRATIONS
from ..services import search_zaken_for_object


class SearchIndexView(LoginRequiredMixin, TemplateView):
    template_name = "search/index.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context.update({"registrations": REGISTRATIONS})
        return context


class SearchForm(forms.Form):
    registration = forms.CharField()
    object_type = forms.CharField()


class SearchView(LoginRequiredMixin, TemplateView):
    template_name = "search/includes/results.html"

    def post(self, request, *args, **kwargs):
        form = SearchForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest(
                content=form.errors.as_json().encode("utf-8"),
                content_type="application/json",
            )

        registration = REGISTRATIONS[form.cleaned_data["registration"]]
        object_type = registration.get_object_type(form.cleaned_data["object_type"])
        object_url = object_type.get_object_url(request.POST)

        zaken = search_zaken_for_object(object_url)

        context = self.get_context_data(zaken=zaken, **kwargs)
        return self.render_to_response(context)
