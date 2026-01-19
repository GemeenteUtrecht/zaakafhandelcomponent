from zac.accounts.permissions import Permission

checklists_schrijven = Permission(
    name="checklist:schrijven",
    description=(
        "Laat toe om checklists bij te werken. Checklists zijn een "
        "verzameling van antwoorden die de vragen van een checklisttype beantwoorden."
    ),
)


checklists_inzien = Permission(
    name="checklist:inzien",
    description=(
        "Laat toe om checklists te lezen. Checklists zijn een "
        "verzameling van antwoorden die de vragen van een checklisttype beantwoorden."
    ),
)

checklisttypes_schrijven = Permission(
    name="checklisttypes:schrijven",
    description=(
        "Laat toe om checklisttypes bij te werken. Checklisttypes zijn een "
        "verzameling van vragen die gerelateerd zijn aan een zaaktype."
    ),
)

checklisttypes_inzien = Permission(
    name="checklisttypes:inzien",
    description=(
        "Laat toe om checklisttypes te lezen. Checklisttypes zijn een "
        "verzameling van vragen die gerelateerd zijn aan een zaaktype."
    ),
)
