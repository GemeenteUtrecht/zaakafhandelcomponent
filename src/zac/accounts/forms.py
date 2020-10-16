from itertools import groupby
from typing import Dict, List, Tuple

from django import forms
from django.core import validators
from django.forms import inlineformset_factory
from django.utils.html import format_html, format_html_join, mark_safe
from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import Catalogus
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.service import get_paginated_results

from zac.core.services import get_informatieobjecttypen, get_zaaktypen

from .models import (
    AuthorizationProfile,
    InformatieobjecttypePermission,
    PermissionSet,
    User,
    UserAuthorizationProfile,
)
from .permissions import registry


def get_catalogus_choices():
    clients = [
        ztc.build_client() for ztc in Service.objects.filter(api_type=APITypes.ztc)
    ]
    all_results = sum(
        [get_paginated_results(client, "catalogus") for client in clients], []
    )

    catalogi = factory(Catalogus, all_results)
    for catalogus in catalogi:
        representation = f"{catalogus.rsin} - {catalogus.domein}"
        yield (catalogus.url, representation)


class SelectCatalogusField(forms.ChoiceField):
    widget = forms.RadioSelect

    def __init__(self, **kwargs):
        max_length = kwargs.pop("max_length")

        super().__init__(choices=get_catalogus_choices, **kwargs)

        self.validators.append(validators.MaxLengthValidator(int(max_length)))


class PermissionSetForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(
        label=_("Permissions"),
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Permissions given."),
    )

    class Meta:
        model = PermissionSet
        fields = (
            "name",
            "description",
            "permissions",
            "catalogus",
            "zaaktype_identificaties",
            "max_va",
        )
        field_classes = {
            "catalogus": SelectCatalogusField,
        }
        widgets = {
            "max_va": forms.RadioSelect,
            "zaaktype_identificaties": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["permissions"].choices = [
            (
                name,
                format_html(
                    "<strong>{name}</strong><br>{description}",
                    name=name,
                    description=permission.description,
                ),
            )
            for name, permission in registry.items()
        ]

    @staticmethod
    def get_zaaktypen() -> Dict[str, List[Tuple[str, str]]]:
        def group_key(zaaktype):
            return zaaktype.catalogus

        _zaaktypen = {}

        zaaktypen = sorted(get_zaaktypen(), key=group_key, reverse=True)
        for catalogus_url, zaaktypen in groupby(zaaktypen, key=group_key):
            seen = set()
            representations = []
            for zaaktype in sorted(
                zaaktypen, key=lambda zt: zt.versiedatum, reverse=True
            ):
                if zaaktype.identificatie in seen:
                    continue
                representations.append((zaaktype.identificatie, zaaktype.omschrijving))
                seen.add(zaaktype.identificatie)

            _zaaktypen[catalogus_url] = representations

        return _zaaktypen

    @staticmethod
    def get_informatieobjecttypen() -> Dict[str, List[Tuple[str, str]]]:
        def group_by(informatieobjecttype):
            return informatieobjecttype.catalogus

        informatieobjecttypen_in_catalogi = sorted(
            get_informatieobjecttypen(), key=group_by, reverse=True
        )

        _informatieobjecttypen = {}
        for catalogus_url, informatieobjecttypen in groupby(
            informatieobjecttypen_in_catalogi, key=group_by
        ):
            # Within a catalog, the omschrijving is unique
            representations = []
            for informatieobjecttype in informatieobjecttypen:
                # The form_field in the template expects a list of tuples (value, label) for each informatieobjecttype
                representations.append(
                    (
                        informatieobjecttype.omschrijving,
                        informatieobjecttype.omschrijving,
                    )
                )
            _informatieobjecttypen[catalogus_url] = representations

        return _informatieobjecttypen

    def get_initial_zaaktypen(self) -> list:
        if not self.instance:
            return []

        return self.instance.zaaktype_identificaties

    @property
    def initial_informatieobjecttypen(self) -> list:
        if not self.instance:
            return []

        return self.instance.informatieobjecttype_omschrijvingen


class InformatieobjecttypeForm(forms.ModelForm):
    selected = forms.BooleanField(required=False)

    class Meta:
        model = InformatieobjecttypePermission
        fields = (
            "id",
            "permission_set",
            "catalogus",
            "omschrijving",
            "max_va",
            "selected",
        )

    def _post_clean(self):
        if (
            not self.cleaned_data.get("selected")
            and self.cleaned_data.get("id") is None
        ):
            return

        return super()._post_clean()


class SerializableFormSet(forms.BaseInlineFormSet):
    @staticmethod
    def catalog_choices() -> List[Tuple[str, str]]:
        """Return the catalogs URL and their label"""
        catalog_choices = list(get_catalogus_choices())
        catalog_choices.insert(0, ("", "------"))
        return catalog_choices


InformatieobjecttypeFormSet = inlineformset_factory(
    PermissionSet,
    InformatieobjecttypePermission,
    can_delete=True,
    form=InformatieobjecttypeForm,
    formset=SerializableFormSet,
)


def get_permission_sets_choices():
    permision_sets = PermissionSet.objects.all()
    for permision_set in permision_sets:
        representation = "<strong>{name} - {va}</strong>{br}{zaaktypen}"
        zaaktypen = format_html_join(
            mark_safe("<br>"),
            "{}",
            [
                (zaaktype.omschrijving,)
                for zaaktype in permision_set.zaaktypen.get_for_presentation()
            ],
        )
        representation = format_html(
            representation,
            name=permision_set.name,
            va=permision_set.get_max_va_display(),
            zaaktypen=zaaktypen,
            br=mark_safe("<br>") if zaaktypen else "",
        )
        yield permision_set.id, representation


class AuthorizationProfileForm(forms.ModelForm):
    class Meta:
        model = AuthorizationProfile
        fields = ("name", "permission_sets", "oo")
        widgets = {"permission_sets": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["permission_sets"].choices = get_permission_sets_choices()


class UserAuthorizationProfileForm(forms.ModelForm):
    class Meta:
        model = UserAuthorizationProfile
        fields = (
            "user",
            "start",
            "end",
        )
        widgets = {
            "user": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        self.auth_profile = kwargs.pop("auth_profile")

        super().__init__(*args, **kwargs)

        self.fields["user"].empty_label = None
        self.fields["user"].queryset = User.objects.exclude(
            id__in=self.auth_profile.user_set.all()
        )

    def save(self, *args, **kwargs):
        self.instance.auth_profile = self.auth_profile
        return super().save(*args, **kwargs)
