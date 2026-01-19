import re


def camelize_discriminators(result, generator, request, public):
    from djangorestframework_camel_case.util import camelize_re, underscore_to_camel

    for component in generator.registry._components.values():
        if "discriminator" in component.schema:
            camelized = re.sub(
                camelize_re,
                underscore_to_camel,
                component.schema["discriminator"]["propertyName"],
            )
            component.schema["discriminator"]["propertyName"] = camelized

    return result
