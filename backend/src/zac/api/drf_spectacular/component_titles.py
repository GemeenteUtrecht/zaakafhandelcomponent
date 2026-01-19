def add_title_to_component_schema(result, generator, request, public):
    for component in generator.registry._components.values():
        component.schema["title"] = component.name

    return result
