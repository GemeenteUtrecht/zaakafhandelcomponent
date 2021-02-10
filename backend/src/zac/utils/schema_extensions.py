from drf_spectacular.extensions import OpenApiFilterExtension
from drf_spectacular.plumbing import build_parameter_type
from drf_spectacular.utils import OpenApiParameter
from rest_framework import fields


class ApiFilterExtension(OpenApiFilterExtension):
    target_class = "zac.utils.filters.ApiFilterBackend"
    match_subclasses = True
    priority = 1

    def get_schema_operation_parameters(self, auto_schema, *args, **kwargs):
        filterset_class = self.target.get_filterset_class(auto_schema.view)
        if not filterset_class:
            return []

        parameters = []
        for field_name, field in filterset_class._filters.items():
            enum = field.choices if isinstance(field, fields.ChoiceField) else []
            parameter_schema = auto_schema._map_serializer_field(field, "request")
            parameters.append(
                build_parameter_type(
                    name=field_name,
                    required=field.required,
                    location=OpenApiParameter.QUERY,
                    description=field.help_text if field.help_text else field_name,
                    schema=parameter_schema,
                    enum=enum,
                )
            )

        return parameters
