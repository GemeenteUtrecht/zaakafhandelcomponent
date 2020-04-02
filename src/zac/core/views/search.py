from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class SearchIndexView(LoginRequiredMixin, TemplateView):
    template_name = "search/index.html"
