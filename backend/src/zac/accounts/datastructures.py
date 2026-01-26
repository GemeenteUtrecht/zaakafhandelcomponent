from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

# Map each VA value to its order (position in the enum definition)
# This is used for permission checking - higher order = more confidential
VA_ORDER = {
    value: index
    for index, (value, _) in enumerate(VertrouwelijkheidsAanduidingen.choices)
}
