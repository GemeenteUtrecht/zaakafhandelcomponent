from django.conf import settings

from elasticsearch_dsl import Document, InnerDoc, Nested, field


class EigenschapDocument(InnerDoc):
    tekst = field.Object()
    getal = field.Object()
    datum = field.Object()
    datum_tijd = field.Object()


class RolDocument(InnerDoc):
    url = field.Keyword()
    betrokkene_type = field.Keyword()
    omschrijving_generiek = field.Keyword()
    betrokkene_identificatie = field.Object(
        properties={"identificatie": field.Keyword()},
        dynamic=False,
    )


class ZaakDocument(Document):
    url = field.Keyword()
    zaaktype = field.Keyword()
    identificatie = field.Keyword()
    bronorganisatie = field.Keyword()
    vertrouwelijkheidaanduiding = field.Text()
    va_order = field.Integer()
    rollen = Nested(RolDocument)

    startdatum = field.Date()
    einddatum = field.Date()
    registratiedatum = field.Date()

    eigenschappen = field.Object(EigenschapDocument)

    class Index:
        name = settings.ES_INDEX_ZAKEN
