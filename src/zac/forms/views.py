from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView

from .forms import SelectFormForm


class SelectFormView(LoginRequiredMixin, FormView):
    form_class = SelectFormForm
    template_name = "forms/select_form.html"

    def form_valid(self, form):
        return redirect(
            "forms:render-form", kwargs={"id": form.cleaned_data["form_id"]}
        )
