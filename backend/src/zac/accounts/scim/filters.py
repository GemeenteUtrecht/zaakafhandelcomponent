from django_scim.filters import FilterQuery
from django_scim.utils import get_group_model


class AuthorizationProfileFilterQuery(FilterQuery):
    model_getter = get_group_model
    attr_map = {
        # attr, sub attr, uri
        ("displayName", None, None): "name",
    }
