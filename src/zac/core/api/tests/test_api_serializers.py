from unittest import TestCase

from django.utils.translation import ugettext_lazy as _

from rest_framework import exceptions, serializers

from ..utils import CSMultipleChoiceField


class TestCSMultipleChoiceField(TestCase):
    def setUp(self):
        self.field = CSMultipleChoiceField()
        self.list = ["1", "2"]
        self.string = "1,2"
        self.choices = tuple((_, _) for _ in self.list)

        self.field_with_choices = CSMultipleChoiceField(
            choices=self.choices, required=True
        )

    def test_field_to_representation_expects_list(self):
        self.assertEqual(self.string, self.field.to_representation(self.list))

        with self.assertRaises(serializers.ValidationError) as cm:
            self.field.to_representation(self.string)

        exception_details = cm.exception.get_full_details()[0]
        self.assertEqual(
            exception_details["message"], "Error: Verwachtte een list maar kreeg str."
        )
        self.assertEqual(exception_details["code"], "invalid")

    def test_field_to_internal_value_expects_str(self):
        self.assertEqual(self.list, self.field.to_internal_value(self.string))

        with self.assertRaises(serializers.ValidationError) as cm:
            self.field.to_internal_value(self.list)

        exception_details = cm.exception.get_full_details()[0]
        self.assertEqual(
            exception_details["message"], "Error: Verwachtte een str maar kreeg list."
        )
        self.assertEqual(exception_details["code"], "invalid")

    def test_field_values_part_of_choices(self):
        self.invalid_string = "2,3"

        with self.assertRaises(serializers.ValidationError) as cm:
            self.field_with_choices.to_internal_value(self.invalid_string)

        exception_details = cm.exception.get_full_details()[0]
        self.assertEqual(
            exception_details["message"],
            "Error: Dit veld bevatte: 3, maar mag alleen een (sub)set zijn van: 1, 2.",
        )
