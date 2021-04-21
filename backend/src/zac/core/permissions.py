from zac.accounts.permissions import Permission

from .blueprints import (
    InformatieObjectTypeBlueprint,
    ZaakHandleBlueprint,
    ZaakTypeBlueprint,
)

zaken_inzien = Permission(
    name="zaken:inzien",
    description="Laat toe om zaken/zaakdossiers in te zien.",
    blueprint_class=ZaakTypeBlueprint,
)

zaken_wijzigen = Permission(
    name="zaken:wijzigen",
    description="Laat het wijzigen toe van zaakattributen.",
    blueprint_class=ZaakTypeBlueprint,
)

zaakproces_usertasks = Permission(
    name="zaakproces:usertasks-uitvoeren",
    description="Usertasks claimen en/of uitvoeren als onderdeel van het zaakproces.",
    blueprint_class=ZaakTypeBlueprint,
)

zaakproces_send_message = Permission(
    name="zaakproces:send-bpmn-message",
    description="BPMN messages versturen in het proces.",
    blueprint_class=ZaakTypeBlueprint,
)


zaken_close = Permission(
    name="zaken:afsluiten",
    description="Zaken afsluiten (=eindstatus zetten), als er een resultaat gezet is.",
    blueprint_class=ZaakTypeBlueprint,
)

zaken_set_result = Permission(
    name="zaken:set-result",
    description="Resultaat zetten op zaken.",
    blueprint_class=ZaakTypeBlueprint,
)

zaken_create_status = Permission(
    name="zaken:create-status",
    description="Status zetten op zaken.",
    blueprint_class=ZaakTypeBlueprint,
)

zaken_download_documents = Permission(
    name="zaken:download-documents",
    description="Inzien documenten bij zaken, inclusief de (binaire) inhoud.",
    blueprint_class=InformatieObjectTypeBlueprint,
)

zaken_add_documents = Permission(
    name="zaken:add-documents",
    description="Nieuwe/extra documenten toevoegen bij zaken.",
    blueprint_class=ZaakTypeBlueprint,
)

zaken_handle_access = Permission(
    name="zaken:toegang-verlenen",
    description="Beheer toegangsverzoeken voor zaken",
    blueprint_class=ZaakHandleBlueprint,
)

zaken_request_access = Permission(
    name="zaken:toegang-aanvragen",
    description="Toegang aanvragen voor zaken",
    blueprint_class=ZaakTypeBlueprint,
)

zaken_add_relations = Permission(
    name="zaken:nieuwe-relaties-toevoegen",
    description="Relateer andere zaken aan de (hoofd)zaak.",
    blueprint_class=ZaakTypeBlueprint,
)
