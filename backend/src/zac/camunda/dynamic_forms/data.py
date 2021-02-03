from dataclasses import dataclass
from datetime import datetime
from typing import List

from zgw_consumers.api_models.zaken import Zaak

from .form_field import FormFieldContext


@dataclass
class BooleanField:
    value: bool


@dataclass
class DateTimeField:
    value: datetime


@dataclass
class IntField:
    value: int


@dataclass
class StringField:
    value: str


@dataclass
class ChoiceField(StringField):
    choices: List[str]


@dataclass
class FormField:
    name: str
    label: str
    input_type: str
    context: FormFieldContext


@dataclass
class DynamicFormContext:
    title: str
    zaak_informatie: Zaak
    form_fields: List[FormField]
