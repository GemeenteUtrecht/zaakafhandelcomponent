from itertools import groupby
from typing import Dict, List, Tuple

from django import forms
from django.core import validators

from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import Catalogus
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.services import get_zaaktypen
from zac.core.utils import get_paginated_results

from .models import PermissionSet


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
