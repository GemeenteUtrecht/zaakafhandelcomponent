from zac.accounts.permissions import Permission

activiteiten_schrijven = Permission(
    name="activiteiten:schrijven",
    description=(
        "Laat toe om activiteiten aan te maken of bij te werken. Activiteiten zijn "
        "willekeurige activiteiten die niet in een BPMN-proces gevat kunnen worden, "
        "en worden geregistreerd bij een specifieke zaak."
    ),
)


activiteiten_inzien = Permission(
    name="activiteiten:inzien",
    description=(
        "Laat toe om activiteiten aan te lezen. Activiteiten zijn "
        "willekeurige activiteiten die niet in een BPMN-proces gevat kunnen worden, "
        "en worden geregistreerd bij een specifieke zaak."
    ),
)
