from django_scim.utils import (
    get_group_adapter,
    get_group_filter_parser,
    get_group_model,
)
from django_scim.views import FilterMixin, GetView, PatchView, SCIMView


class GroupsView(FilterMixin, PatchView, GetView, SCIMView):
    """
    We don't need the POST/PUT/DELETE methods, as the only operations for AuthorizationProfile that we want to allow are
    to read and to add/remove users from a profile (in SCIM terms: add/remove members to a group)
    """

    http_method_names = ["get", "patch"]

    scim_adapter_getter = get_group_adapter
    model_cls_getter = get_group_model
    parser_getter = get_group_filter_parser
