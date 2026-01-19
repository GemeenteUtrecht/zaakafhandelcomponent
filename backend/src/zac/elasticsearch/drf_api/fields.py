from rest_framework.fields import MultipleChoiceField


class OrderedMultipleChoiceField(MultipleChoiceField):
    def to_representation(self, value):
        values = super().to_representation(value)
        return sorted(list(values))
