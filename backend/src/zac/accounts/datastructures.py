from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

VA_ORDER = {
    value: VertrouwelijkheidsAanduidingen.get_choice(value).order
    for value, _ in VertrouwelijkheidsAanduidingen.choices
}
