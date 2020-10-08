from elasticsearch_dsl import Document, Text


class ZaakDocument(Document):
    url = Text()
    zaaktype = Text()
    vertrouwelijkheidaanduiding = Text()

    class Index:
        name = "zaken"
