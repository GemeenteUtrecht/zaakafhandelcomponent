from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView

from .client import OpenFormsClient
from .forms import SelectFormForm, generate_form_class


class SelectFormView(LoginRequiredMixin, FormView):
    form_class = SelectFormForm
    template_name = "forms/select_form.html"

    def form_valid(self, form):
        return redirect("forms:render-form", form_id=form.cleaned_data["form_id"])


class RenderFormView(LoginRequiredMixin, FormView):
    template_name = "forms/rendered_form.html"

    def get_form_class(self):
        return generate_form_class(self.kwargs["form_id"])

    def form_valid(self, form):
        raise NotImplementedError("Not yet")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        client = OpenFormsClient()
        form_definition = client.get(f"forms/{self.kwargs['form_id']}")

        context.update(
            {
                "form_name": form_definition["name"],
            }
        )
        return context
