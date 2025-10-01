from django.conf import settings

from elasticsearch_dsl import (
    Document,
    InnerDoc,
    MetaField,
    Nested,
    analyzer,
    char_filter,
    field,
    token_filter,
    tokenizer,
)

truncate_filter = token_filter(
    "truncate", type="truncate", length=f"{settings.MAX_GRAM-settings.MIN_GRAM}"
)
dutch_stop_filter = token_filter("dutch_stop", type="stop", stopwords="_dutch_")
ngram_tokenizer = tokenizer(
    "zacGram",
    "ngram",
    min_gram=settings.MIN_GRAM,
    max_gram=settings.MAX_GRAM,
)
ngram_analyzer = analyzer(
    "ngram_analyzer",
    tokenizer=ngram_tokenizer,
    filter=["lowercase", dutch_stop_filter],
)
strip_leading_zeros_in_zaakidentificatie_filter = char_filter(
    "strip_leading_zeros",
    type="pattern_replace",
    pattern="(^ZAAK-[0-9]+-)(0+)([1-9][0-9]+)",
    replacement="$1$3",
)
strip_leading_zeros_in_zaakidentificatie_analyzer = analyzer(
    "strip_leading_zeros",
    tokenizer="standard",
    filter=["lowercase"],
    char_filter=[strip_leading_zeros_in_zaakidentificatie_filter],
)
standard_dutch_analyzer = analyzer(
    "standard",
    tokenizer="standard",
    filter=["lowercase", dutch_stop_filter],
)


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
    catalogus_domein = field.Keyword()
    omschrijving = field.Keyword()
    identificatie = field.Keyword()


class StatusDocument(InnerDoc):
    url = field.Keyword()
    statustype = field.Keyword()
    datum_status_gezet = field.Date()
    statustoelichting = field.Text(fields={"keyword": field.Keyword()})


class ZaakObjectDocument(Document):
    url = field.Keyword()
    object = field.Keyword()
    zaak = field.Keyword()

    class Index:
        name = settings.ES_INDEX_ZO
        settings = {
            "index.mapping.ignore_malformed": True,
        }


class ZaakInformatieObjectDocument(Document):
    url = field.Keyword()
    informatieobject = field.Keyword()
    zaak = field.Keyword()

    class Index:
        name = settings.ES_INDEX_ZIO
        settings = {
            "index.mapping.ignore_malformed": True,
        }


class ZaakDocument(Document):
    url = field.Keyword()
    zaaktype = field.Object(ZaakTypeDocument)
    identificatie = field.Text(
        fields={"keyword": field.Keyword()},
        analyzer=strip_leading_zeros_in_zaakidentificatie_analyzer,
    )
    bronorganisatie = field.Keyword()
    omschrijving = field.Text(
        fields={"keyword": field.Keyword()},
        analyzer=ngram_analyzer,
        search_analyzer=standard_dutch_analyzer,
    )
    vertrouwelijkheidaanduiding = field.Text(fields={"keyword": field.Keyword()})
    va_order = field.Integer()
    rollen = Nested(RolDocument)
    startdatum = field.Date()
    einddatum = field.Date()
    registratiedatum = field.Date()
    deadline = field.Date()
    eigenschappen = field.Object(EigenschapDocument)
    status = field.Object(StatusDocument)
    toelichting = field.Text(fields={"keyword": field.Keyword()})
    zaakgeometrie = field.GeoShape()
    has_eindstatus = field.Boolean()

    class Index:
        name = settings.ES_INDEX_ZAKEN
        settings = {
            "index.mapping.ignore_malformed": True,
            "index.mapping.nested_objects.limit": 20000,  # temporary upscale to 20.000 to offset `mistake?` in `verzaking`
            "max_ngram_diff": settings.MAX_GRAM - settings.MIN_GRAM,
        }
        analyzers = [
            ngram_analyzer,
            standard_dutch_analyzer,
            strip_leading_zeros_in_zaakidentificatie_analyzer,
        ]

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


class RelatedZaakDocument(InnerDoc):
    bronorganisatie = field.Keyword(index=False)
    identificatie = field.Keyword(index=False)
    omschrijving = field.Text(index=False)
    url = field.Keyword()
    va_order = field.Integer()
    zaaktype = field.Object(ZaakTypeDocument)


class ObjectTypeDocument(InnerDoc):
    name = field.Keyword()
    url = field.Keyword()


class ObjectDocument(Document):
    url = field.Keyword()
    type = field.Object(ObjectTypeDocument)
    record_data = field.Object()
    related_zaken = Nested(RelatedZaakDocument)
    string_representation = field.Text(index=False)

    class Index:
        name = settings.ES_INDEX_OBJECTEN
        settings = {
            "index.mapping.ignore_malformed": True,
            "max_ngram_diff": settings.MAX_GRAM - settings.MIN_GRAM,
        }
        analyzers = [ngram_analyzer, standard_dutch_analyzer]

    class Meta:
        dynamic_templates = MetaField(
            [
                {
                    "record_data": {
                        "path_match": "record_data.*",
                        "match_mapping_type": "string",
                        "mapping": {
                            "type": "text",
                            "analyzer": ngram_analyzer,
                            "search_analyzer": standard_dutch_analyzer,
                            "copy_to": "record_data_text.*",
                        },
                    }
                },
                {
                    "record_data_text": {
                        "path_match": "record_data_text.*",
                        "mapping": {
                            "type": "text",
                            "analyzer": ngram_analyzer,
                            "search_analyzer": standard_dutch_analyzer,
                        },
                    },
                },
            ]
        )


class InformatieObjectTypeDocument(InnerDoc):
    url = field.Keyword()
    begin_geldigheid = field.Date()
    catalogus = field.Keyword()
    concept = field.Boolean()
    einde_geldigheid = field.Date()
    omschrijving = field.Text(
        fields={"keyword": field.Keyword()},
        analyzer=ngram_analyzer,
        search_analyzer=standard_dutch_analyzer,
    )
    vertrouwelijkheidaanduiding = field.Keyword()


class InformatieObjectDocument(Document):
    auteur = field.Keyword()
    beschrijving = field.Text(
        fields={"keyword": field.Keyword()},
        analyzer=ngram_analyzer,
        search_analyzer=standard_dutch_analyzer,
    )
    bestandsnaam = field.Keyword()
    bestandsomvang = field.Integer()
    bronorganisatie = field.Keyword()
    creatiedatum = field.Date()
    formaat = field.Keyword()
    identificatie = field.Keyword()
    indicatie_gebruiksrecht = field.Boolean()
    inhoud = field.Keyword()
    integriteit = field.Object()
    link = field.Keyword()
    locked = field.Boolean()
    ondertekening = field.Object()
    ontvangstdatum = field.Date()
    status = field.Keyword()
    taal = field.Keyword()
    titel = field.Text(
        fields={"keyword": field.Keyword()},
        analyzer=ngram_analyzer,
        search_analyzer=standard_dutch_analyzer,
    )
    url = field.Keyword()
    versie = field.Integer()
    verzenddatum = field.Date()

    informatieobjecttype = field.Object(InformatieObjectTypeDocument)
    related_zaken = Nested(RelatedZaakDocument)
    last_edited_date = field.Date()
    vertrouwelijkheidaanduiding = field.Keyword()

    class Index:
        name = settings.ES_INDEX_DOCUMENTEN
        settings = {
            "index.mapping.ignore_malformed": True,
            "max_ngram_diff": settings.MAX_GRAM - settings.MIN_GRAM,
        }
