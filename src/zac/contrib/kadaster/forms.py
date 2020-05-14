from django import forms


class BagObjectSelectieWidget(forms.URLInput):
    template_name = "kadaster/forms/widgets/bag_object_selectie.html"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs)

        self.attrs.setdefault("class", "")
        self.attrs["class"] += " bag-object-selection__value"


class BagObjectSelectieField(forms.URLField):
    widget = BagObjectSelectieWidget
