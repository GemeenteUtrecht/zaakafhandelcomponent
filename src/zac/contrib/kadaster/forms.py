from django import forms


class PandSelectieWidget(forms.URLInput):
    template_name = "kadaster/forms/widgets/pand_selectie.html"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs)

        self.attrs.setdefault("class", "")
        self.attrs["class"] += " pand-selection__value"


class PandSelectieField(forms.URLField):
    widget = PandSelectieWidget
