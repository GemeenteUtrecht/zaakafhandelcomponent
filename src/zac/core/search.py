from dataclasses import dataclass
from typing import List, Tuple, Type

from django.forms import TextInput, Widget
from django.http import QueryDict

from furl import furl

from zac.contrib.kadaster.forms import BagObjectSelectieWidget


def _clean_url(url: str) -> str:
    furled = furl(url)
    # Delete the geldigOp querystring, which contains the date the BAG object was retrieved.
    # It's still the same BAG object, but might a different representation on another date.
    # Dropping the QS allows the zaakobject list filter to work when passing in the
    # object to find related zaken.
    if "geldigOp" in furled.args:
        del furled.args["geldigOp"]
    return furled.url


@dataclass
class ObjectType:
    value: str
    label: str
    widget: Type[Widget]

    def render_widget(self) -> str:
        widget = self.widget()
        return widget.render(name=self.value, value="")

    def get_object_url(self, data: QueryDict) -> str:
        object_url = data[self.value]
        # TODO: make this configurable
        return _clean_url(object_url)


@dataclass
class Registration:
    label: str
    object_types: List[ObjectType]

    @property
    def object_type_choices(self) -> List[Tuple[str, str]]:
        return [
            (object_type.value, object_type.label) for object_type in self.object_types
        ]

    def get_object_type(self, object_type: str):
        object_type = next((ot for ot in self.object_types if ot.value == object_type))
        return object_type


REGISTRATIONS = {
    "bag": Registration(
        label="BAG",
        object_types=[
            ObjectType(value="pand", label="Pand", widget=BagObjectSelectieWidget),
            ObjectType(
                value="verblijfsobject",
                label="Verblijfs object",
                widget=BagObjectSelectieWidget,
            ),
            ObjectType(value="address", label="Adres (TODO)", widget=TextInput),
            ObjectType(
                value="geometry",
                label="Vrije geo-zoekopdracht (TODO)",
                widget=TextInput,
            ),
        ],
    ),
    "brp": Registration(label="BRP", object_types=[]),
    "bgt_brt": Registration(label="BGT/BRT", object_types=[]),
}
