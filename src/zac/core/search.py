from dataclasses import dataclass
from typing import List, Tuple, Type
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.forms import TextInput, Widget
from django.http import QueryDict

from zac.contrib.kadaster.forms import PandSelectieWidget


def _clean_url(url: str) -> str:
    scheme, netloc, path, query, fragment = urlsplit(url)
    query_dict = parse_qs(query)

    # Delete the geldigOp querystring, which contains the date the pand was retrieved.
    # It's still the same pand, but might a different representation on another date.
    # Dropping the QS allows the zaakobject list filter to work when passing in the
    # object to find related zaken.
    if "geldigOp" in query_dict:
        del query_dict["geldigOp"]

    query = urlencode(query_dict, doseq=True)
    return urlunsplit((scheme, netloc, path, query, fragment))


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
            ObjectType(value="pand", label="Pand", widget=PandSelectieWidget),
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
