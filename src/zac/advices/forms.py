from django import forms

from django_camunda.api import get_process_instance_variable

from zac.core.cache import invalid_zio_cache, invalidate_zaak_cache
from zac.core.forms import TaskFormMixin, _repr
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


class DocDescWidget(forms.TextInput):
    template_name = "advices/forms/widgets/doc_title.html"


class UploadDocumentForm(forms.Form):
    url = forms.CharField(widget=forms.HiddenInput())
    identificatie = forms.CharField(widget=forms.HiddenInput())
    document = forms.CharField(
        widget=DocDescWidget(), disabled=True, label="Source document"
    )
    upload = forms.FileField(
        widget=forms.FileInput(), label="Upload edited document", required=False
    )

    def clean(self):
        if self.has_changed() and "url" in self.changed_data:
            raise forms.ValidationError("Url should not be changed")


class UploadDocumentBaseFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop("task")
        self.user = kwargs.pop("user")

        # retrieve process instance variables
        zaak_url = get_process_instance_variable(
            self.task.process_instance_id, "zaakUrl"
        )
        zaak = get_zaak(zaak_url=zaak_url)
        documenten, _ = get_documenten(zaak)
        self.zaak = zaak

        initial = [
            {"url": doc.url, "document": _repr(doc), "identificatie": doc.identificatie}
            for doc in documenten
        ]
        kwargs.setdefault("initial", initial)

        super().__init__(*args, **kwargs)

    def on_submission(self):
        assert self.is_valid(), "FormSet must be validated first"

        changed = False
        for form in self.forms:
            if form.has_changed() and form.cleaned_data["upload"]:
                changed = True
                data = {
                    "auteur": self.user.username,
                    "identificatie": form.cleaned_data["identificatie"],
                }
                update_document(
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
