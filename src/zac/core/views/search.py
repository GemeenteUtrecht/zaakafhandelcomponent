from dataclasses import dataclass
from typing import List, Tuple, Type

from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import TextInput, Widget
from django.views.generic import TemplateView

from zac.contrib.kadaster.forms import PandSelectieWidget


@dataclass
class ObjectType:
    value: str
    label: str
    widget: Type[Widget]

    def render_widget(self) -> str:
        widget = self.widget()
        return widget.render(name=self.value, value="")


@dataclass
class Registration:
    label: str
    object_types: List[ObjectType]

    @property
    def object_type_choices(self) -> List[Tuple[str, str]]:
        return [
            (object_type.value, object_type.label) for object_type in self.object_types
        ]


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


class SearchView(LoginRequiredMixin, TemplateView):
    template_name = "search/includes/results.html"

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)
