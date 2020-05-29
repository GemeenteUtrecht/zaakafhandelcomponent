from django import forms

from django_camunda.api import get_process_instance_variable

from zac.core.forms import TaskFormMixin, _repr
from zac.core.services import get_documenten, get_zaak

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
    doc_id = forms.CharField()
    new_version = forms.FileField()


UploadDocumentFormset = forms.formset_factory(UploadDocumentForm, extra=1)
