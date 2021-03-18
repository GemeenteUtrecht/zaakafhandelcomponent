from django.conf import settings

from elasticsearch_dsl import Document, InnerDoc, MetaField, Nested, field


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


class ZaakTypeDocument(InnerDoc):
    url = field.Keyword()
    catalogus = field.Keyword()
    omschrijving = field.Keyword()


class ZaakDocument(Document):
    url = field.Keyword()
    zaaktype = field.Object(ZaakTypeDocument)
    identificatie = field.Keyword()
    bronorganisatie = field.Keyword()
    omschrijving = field.Text()
    vertrouwelijkheidaanduiding = field.Text()
    va_order = field.Integer()
    rollen = Nested(RolDocument)

    startdatum = field.Date()
    einddatum = field.Date()
    registratiedatum = field.Date()

    eigenschappen = field.Object(EigenschapDocument)

    class Index:
        name = settings.ES_INDEX_ZAKEN
        settings = {"index.mapping.ignore_malformed": True}

    class Meta:
        dynamic_templates = MetaField(
            [
                {
                    "eigenschap_string": {
                        "path_match": "eigenschappen.tekst.*",
                        "mapping": {"type": "keyword"},
                    }
                },
                {
                    "eigenschap_number": {
                        "path_match": "eigenschappen.getal.*",
                        "mapping": {"type": "integer"},
                    }
                },
                {
                    "eigenschap_date": {
                        "path_match": "eigenschappen.datum.*",
                        "mapping": {"type": "date"},
                    }
                },
                {
                    "eigenschap_datetime": {
                        "path_match": "eigenschappen.datum_tijd.*",
                        "mapping": {"type": "date"},
                    }
                },
            ]
        )
