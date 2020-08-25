from django import forms
from django.utils.translation import gettext_lazy as _

from django_camunda.api import get_process_instance_variable

from zac.camunda.forms import TaskFormMixin
from zac.core.fields import DocumentsMultipleChoiceField


class ConfigurePackageForm(TaskFormMixin, forms.Form):
    documenten = DocumentsMultipleChoiceField(
        label=_("Te ondertekenen documenten"),
        help_text=_(
            "Dit zijn de documenten die bij de zaak horen. Selecteer de documenten "
            "die digitaal ondertekend moeten worden."
        ),
    )

    template_name = "validsign/configure_package.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # retrieve process instance variables
        zaak_url = get_process_instance_variable(
            self.task.process_instance_id, "zaakUrl"
        )
        self.fields["documenten"].zaak = zaak_url
