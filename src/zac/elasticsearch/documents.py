from elasticsearch_dsl import Document, InnerDoc, Nested, field


class RolDocument(InnerDoc):
    url = field.Text()
    betrokkene_type = field.Text
    betrokkene_identificatie = field.Object()


class ZaakDocument(Document):
    url = field.Text()
    zaaktype = field.Text()
    identificatie = field.Text()
    bronorganisatie = field.Text()
    vertrouwelijkheidaanduiding = field.Text()
    va_order = field.Integer()
    rollen = Nested(RolDocument)

    class Index:
        # TODO put index name into settings and env vars
        name = "zaken"
