from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

VA_ORDER = {
    val: _
    for val, _ in zip(
        VertrouwelijkheidsAanduidingen.values,
        range(24, 24 + len(VertrouwelijkheidsAanduidingen.values)),
    )
}
