from typing import Dict, Union

from django.core.cache import cache

from zac.core.models import MetaObjectTypesConfig


def get_field_names_and_values_meta_object_types() -> Dict[Union[int, str], str]:
    conf = MetaObjectTypesConfig.get_solo()
    return {getattr(conf, field.name): field.name for field in conf._meta.fields}


def invalidate_meta_objects(on_data: Dict):
    mapping = get_field_names_and_values_meta_object_types()
    if key := on_data["kenmerken"]["object_type"] in mapping.get(
        on_data["kenmerken"]["object_type"]
    ):
        cache.delete(key)
