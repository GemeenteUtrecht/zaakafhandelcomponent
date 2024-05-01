from djchoices import ChoiceItem, DjangoChoices


class IndexTypes(DjangoChoices):
    index_all = ChoiceItem("index_all", "index_all")
    index_documenten = ChoiceItem("index_documenten", "index_documenten")
    index_objecten = ChoiceItem("index_objecten", "index_objecten")
    index_zaakinformatieobjecten = ChoiceItem(
        "index_zaakinformatieobjecten", "index_zaakinformatieobjecten"
    )
    index_zaakobjecten = ChoiceItem("index_zaakobjecten", "index_zaakobjecten")
    index_zaken = ChoiceItem("index_zaken", "index_zaken")
