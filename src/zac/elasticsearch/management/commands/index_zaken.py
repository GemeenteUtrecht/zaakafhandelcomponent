from django.core.management import BaseCommand

from elasticsearch import exceptions
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.accounts.models import User
from zac.accounts.permissions import UserPermissions
from zac.core.services import get_rollen_all, get_zaken

from ...documents import RolDocument, ZaakDocument


class Command(BaseCommand):
    help = "Create documents in ES by indexing all zaken from ZAKEN API"

    def handle(self, **options):
        # todo remove zaken which were deleted in the API
        self.index_zaken()
        self.index_rollen()

        self.stdout.write("Zaken have been indexed")

    def index_zaken(self):
        # create/refresh mapping in the ES
        ZaakDocument.init()

        user, _ = User.objects.get_or_create(username="elastic", is_superuser=True)
        user_perms = UserPermissions(user)

        zaken = get_zaken(user_perms, find_all=True)
        self.stdout.write(f"{len(zaken)} zaken are received from Zaken API")

        # TODO replace with bulk API
        for zaak in zaken:
            zaak_document = ZaakDocument(
                meta={"id": zaak.uuid},
                url=zaak.url,
                zaaktype=zaak.zaaktype.url,
                identificatie=zaak.identificatie,
                bronorganisatie=zaak.bronorganisatie,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
                va_order=VertrouwelijkheidsAanduidingen.get_choice(
                    zaak.vertrouwelijkheidaanduiding
                ).order,
            )
            zaak_document.save()

    def index_rollen(self):
        rollen = get_rollen_all()
        self.stdout.write(f"{len(rollen)} rollen are received from Zaken API")

        for rol in rollen:
            rol_document = RolDocument(
                url=rol.url,
                betrokkene_type=rol.betrokkene_type,
                # TODO replace with get_identificatie after rebase on oo branch
                betrokkene_identificatie=rol.betrokkene_identificatie,
            )

            # add rol document to zaak
            zaak_uuid = rol.zaak.strip("/").split("/")[-1]
            try:
                zaak_document = ZaakDocument.get(id=zaak_uuid)
            except exceptions.NotFoundError as exc:
                self.stdout.write(f"Warning: {exc}")
                continue

            zaak_document.rollen.append(rol_document)
            zaak_document.save()
