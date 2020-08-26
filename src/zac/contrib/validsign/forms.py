from django import forms
from django.utils.translation import gettext_lazy as _

from django_camunda.api import get_process_instance_variable

from zac.accounts.models import User
from zac.camunda.forms import BaseTaskFormSet, TaskFormMixin
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


class SignerForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        label=_("Medewerker"),
        help_text=_("Selecteer een medewerker."),
    )
    email = forms.EmailField(
        required=False,
        label=_("email address"),
        help_text=_(
            "De ondertekenaar ontvangt op dit e-mailadres een uitnoding ter ondertekening."
        ),
    )
    first_name = forms.CharField(
        required=False,
        label=_("voornaam"),
        help_text=_("De voornaam van de ondertekenaar."),
    )
    last_name = forms.CharField(
        required=False,
        label=_("achternaam"),
        help_text=_("De achternaam van de ondertekenaar."),
    )

    def clean(self):
        super().clean()

        user = self.cleaned_data.get("user")
        email = self.cleaned_data.get("email")
        first_name = self.cleaned_data.get("first_name")
        last_name = self.cleaned_data.get("last_name")

        if user:
            if not user.email and not email:
                self.add_error(
                    "email",
                    _(
                        "We kennen geen e-mailadres voor deze gebruiker. Geef aub een email op."
                    ),
                )
            if not user.first_name and not first_name:
                self.add_error(
                    "first_name",
                    _(
                        "We kennen geen voornaam voor deze gebruiker. Geef aub een voornaam op."
                    ),
                )
            if not user.last_name and not last_name:
                self.add_error(
                    "last_name",
                    _(
                        "We kennen geen achternaam voor deze gebruiker. Geef aub een achternaam op."
                    ),
                )
        elif not (email and first_name and last_name):
            self.add_error(
                None,
                _(
                    "Selecteer een gebruiker of geef een e-mailadres, voornaam en achternaam op."
                ),
            )
        else:
            self.cleaned_data["email"] = email or user.email
            self.cleaned_data["first_name"] = first_name or user.first_name
            self.cleaned_data["last_name"] = last_name or user.last_name


class BaseSignerFormSet(BaseTaskFormSet):
    def get_process_variables(self) -> dict:
        signers = []
        for signer_data in self.cleaned_data:
            if not signer_data:  # empty form
                continue

            signers.append(
                {
                    "email": signer_data["email"],
                    "firstName": signer_data["first_name"],
                    "lastName": signer_data["last_name"],
                }
            )

        return {
            "signers": signers,
        }


SignerFormSet = forms.formset_factory(SignerForm, formset=BaseSignerFormSet, extra=1)
