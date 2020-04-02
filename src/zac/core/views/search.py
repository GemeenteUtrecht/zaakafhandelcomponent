from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from djchoices import ChoiceItem, DjangoChoices


class BagTypes(DjangoChoices):
    pand = ChoiceItem("pand", "Pand")
    address = ChoiceItem("address", "Adres (TODO)")
    geometry = ChoiceItem("geometry", "Vrije geo-zoekopdracht (TODO)")


REGISTRATIONS = {
    "bag": {"label": "BAG", "object_types": BagTypes.choices,},
    "brp": {"label": "BRP", "object_types": [],},
    "bgt_brt": {"label": "BGT/BRT", "object_types": [],},
}


class SearchIndexView(LoginRequiredMixin, TemplateView):
    template_name = "search/index.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context.update({"registrations": REGISTRATIONS})
        return context
