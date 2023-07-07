from zac.accounts.permissions import Permission

zaken_aanmaken = Permission(
    name="zaken:aanmaken",
    description="Laat toe om zaken aan te maken.",
)

zaken_inzien = Permission(
    name="zaken:inzien",
    description="Laat toe om zaken/zaakdossiers in te zien.",
)

zaken_wijzigen = Permission(
    name="zaken:wijzigen",
    description="Laat het wijzigen toe van zaakattributen.",
)

zaakprocess_starten = Permission(
    name="zaakproces:starten",
    description="Het zaakproces in camunda starten.",
)

zaakproces_usertasks = Permission(
    name="zaakproces:usertasks-uitvoeren",
    description="Usertasks claimen en/of uitvoeren als onderdeel van het zaakproces.",
)

zaakproces_send_message = Permission(
    name="zaakproces:send-bpmn-message",
    description="BPMN messages versturen in het proces.",
)

zaken_close = Permission(
    name="zaken:afsluiten",
    description="Zaken afsluiten (=eindstatus zetten), als er een resultaat gezet is.",
)

zaken_set_result = Permission(
    name="zaken:set-result",
    description="Resultaat zetten op zaken.",
)

zaken_create_status = Permission(
    name="zaken:create-status",
    description="Status zetten op zaken.",
)
zaken_list_documents = Permission(
    name="zaken:lijst-documenten",
    description="Inzien documentenlijst bij zaken, exclusief de (binaire) inhoud.",
)
zaken_download_documents = Permission(
    name="zaken:download-documents",
    description="Inzien documenten bij zaken, inclusief de (binaire) inhoud.",
)

zaken_update_documents = Permission(
    name="zaken:update-documents",
    description="Bewerken van eigenschappen van de documenten bij zaken.",
)

zaken_add_documents = Permission(
    name="zaken:add-documents",
    description="Nieuwe/extra documenten toevoegen bij zaken.",
)

zaken_handle_access = Permission(
    name="zaken:toegang-verlenen",
    description="Beheer toegangsverzoeken voor zaken",
)

zaken_add_relations = Permission(
    name="zaken:nieuwe-relaties-toevoegen",
    description="Relateer andere zaken aan de (hoofd)zaak.",
)

zaken_geforceerd_bijwerken = Permission(
    name="zaken:geforceerd-bijwerken",
    description="Kan een zaak bijwerken zelfs als deze afgesloten is.",
)
