from django.conf import settings

from elasticsearch_dsl import Document, InnerDoc, Nested, field


class RolDocument(InnerDoc):
    url = field.Keyword()
    betrokkene_type = field.Keyword()
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
    registratiedatum = field.Date()

    class Index:
        name = settings.ES_INDEX_ZAKEN
