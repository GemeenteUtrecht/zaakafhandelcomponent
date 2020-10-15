from django.conf import settings

from elasticsearch_dsl import Document, InnerDoc, Nested, field


class RolDocument(InnerDoc):
    url = field.Text()
    betrokkene_type = field.Text
    betrokkene_identificatie = field.Object()


class ZaakDocument(Document):
    url = field.Keyword()
    zaaktype = field.Keyword()
    identificatie = field.Keyword()
    bronorganisatie = field.Keyword()
    vertrouwelijkheidaanduiding = field.Text()
    va_order = field.Integer()
    rollen = Nested(RolDocument)

    class Index:
        name = settings.ES_INDEX_ZAKEN
