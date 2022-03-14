from zac.accounts.permissions import Permission

checklists_bijwerken = Permission(
    name="checklist:schrijven",
    description=(
        "Laat toe om checklists bij te werken. Checklists zijn een"
        "verzameling van vragen die gerelateerd zijn aan een zaaktype."
    ),
)


checklists_inzien = Permission(
    name="checklist:inzien",
    description=(
        "Laat toe om checklists te lezen. Checklists zijn een"
        "verzameling van vragen die gerelateerd zijn aan een zaaktype."
    ),
)
