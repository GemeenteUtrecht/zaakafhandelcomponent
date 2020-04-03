from dataclasses import dataclass
from typing import List, Tuple, Type
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import TextInput, Widget
from django.http import HttpResponseBadRequest, QueryDict
from django.views.generic import TemplateView

from zac.contrib.kadaster.forms import PandSelectieWidget

from ..services import search_zaken_for_object


def _clean_url(url: str) -> str:
    scheme, netloc, path, query, fragment = urlsplit(url)
    query_dict = parse_qs(query)

    # Delete the geldigOp querystring, which contains the date the pand was retrieved.
    # It's still the same pand, but might a different representation on another date.
    # Dropping the QS allows the zaakobject list filter to work when passing in the
    # object to find related zaken.
    if "geldigOp" in query_dict:
        del query_dict["geldigOp"]

    query = urlencode(query_dict, doseq=True)
    return urlunsplit((scheme, netloc, path, query, fragment))


@dataclass
class ObjectType:
    value: str
    label: str
    widget: Type[Widget]

    def render_widget(self) -> str:
        widget = self.widget()
        return widget.render(name=self.value, value="")

    def get_object_url(self, data: QueryDict) -> str:
        object_url = data[self.value]
        # TODO: make this configurable
        return _clean_url(object_url)


@dataclass
class Registration:
    label: str
    object_types: List[ObjectType]

    @property
    def object_type_choices(self) -> List[Tuple[str, str]]:
        return [
            (object_type.value, object_type.label) for object_type in self.object_types
        ]

    def get_object_type(self, object_type: str):
        object_type = next((ot for ot in self.object_types if ot.value == object_type))
        return object_type


REGISTRATIONS = {
    "bag": Registration(
        label="BAG",
        object_types=[
            ObjectType(value="pand", label="Pand", widget=PandSelectieWidget),
            ObjectType(value="address", label="Adres (TODO)", widget=TextInput),
            ObjectType(
                value="geometry",
                label="Vrije geo-zoekopdracht (TODO)",
                widget=TextInput,
            ),
        ],
    ),
    "brp": Registration(label="BRP", object_types=[]),
    "bgt_brt": Registration(label="BGT/BRT", object_types=[]),
}


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
