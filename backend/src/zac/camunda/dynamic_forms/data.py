from dataclasses import dataclass
from xml.etree.ElementTree import Element


@dataclass
class CamundaFormField:
    element: Element

    @property
    def id(self) -> str:
        return self.element.attrib["id"]
