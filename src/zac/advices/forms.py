from django import forms

from django_camunda.api import get_process_instance_variable

from zac.core.cache import invalid_zio_cache, invalidate_zaak_cache
from zac.core.forms import TaskFormMixin
from zac.core.services import get_documenten, get_zaak, update_document

from .constants import AdviceObjectTypes
from .models import Advice


class AdviceForm(TaskFormMixin, forms.ModelForm):
    class Meta:
        model = Advice
        fields = (
            "advice",
            "accord",
        )

    def on_submission(self):
        assert self.is_valid(), "Form must be validated first"
        self.instance.user = self.context["request"].user

        # fetch the zaak that it applies to
        zaak_url = get_process_instance_variable(
            self.task.process_instance_id, "zaakUrl"
        )
        self.instance.object_type = AdviceObjectTypes.zaak
        self.instance.object_url = zaak_url

        self.save()

    def get_process_variables(self):
        # does not set any variables
        return {}


class UploadDocumentForm(forms.Form):
    url = forms.CharField(widget=forms.HiddenInput())
    titel = forms.CharField()
    upload = forms.FileField(
        widget=forms.FileInput(), label="Upload new version", required=False
    )


class UploadDocumentBaseFormSet(forms.BaseFormSet):
    def __init__(self, task, user, *args, **kwargs):
        self.task = task
        self.user = user

        if "initial" in kwargs:
            super().__init__(**kwargs)

        # retrieve process instance variables
        zaak_url = get_process_instance_variable(
            self.task.process_instance_id, "zaakUrl"
        )
        zaak = get_zaak(zaak_url=zaak_url)
        documenten, _ = get_documenten(zaak)

        initial = [{"url": doc.url, "titel": doc.titel} for doc in documenten]
        kwargs["initial"] = initial

        self.zaak = zaak

        super().__init__(*args, **kwargs)

    def on_submission(self):
        assert self.is_valid(), "FormSet must be validated first"

        changed = False
        for form in self.forms:
            if form.has_changed() and form.cleaned_data["upload"]:
                changed = True
                data = {
                    "titel": form.cleaned_data["titel"],
                    "auteur": self.user.username,
                }
                document = update_document(
                    url=form.cleaned_data["url"],
                    data=data,
                    file=form.cleaned_data["upload"],
                )

        if changed:
            invalidate_zaak_cache(self.zaak)
            invalid_zio_cache(self.zaak)


UploadDocumentFormset = forms.formset_factory(
    UploadDocumentForm, formset=UploadDocumentBaseFormSet, extra=0
)
