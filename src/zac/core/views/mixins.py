from typing import List

from django.core.exceptions import PermissionDenied
from django.db.models import Q

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document

from zac.accounts.models import PermissionSet, User


class DocumentPermissionMixin:
    @staticmethod
    def check_document_permissions(document: Document, user: User):
        """Check if a user has the permission to see a document

        This does the following:
        1. Checks that the user has permissions for the catalogus in which the informatieobjecttype is located.
            If no informatieobjecttype_catalogus are specified, then the user has no access.
        2.  Checks that the user has permission for the specified informatieobjecttype of the document.
            If the PermissionSet has a catalog specified but no informatieobjecttypes, then all informatieobjecttypes in
            the catalog are allowed.
            If the PermissionSet has a catalog specified _and_ a set of informatieobjecttypes, only the specified
            informatieobjecttypes are allowed.
        3. Checks that the user has level of confidentiality greater or equal to that specified in the informatieobjecttype.
        """
        document_va = VertrouwelijkheidsAanduidingen.get_choice(
            document.informatieobjecttype.vertrouwelijkheidaanduiding
        ).order

        order_case = VertrouwelijkheidsAanduidingen.get_order_expression(
            "informatieobjecttype_max_va"
        )

        required_permissions = (
            PermissionSet.objects.filter(
                Q(
                    informatieobjecttype_omschrijvingen__contains=[
                        document.informatieobjecttype.omschrijving
                    ]
                )
                | Q(informatieobjecttype_omschrijvingen=[]),
                informatieobjecttype_catalogus=document.informatieobjecttype.catalogus,
            )
            .annotate(iot_va_order=order_case)
            .filter(iot_va_order__gte=document_va)
        )

        user_authorisation_profiles = user.auth_profiles.filter(
            permission_sets__in=required_permissions
        )
        if not user_authorisation_profiles.exists():
            error_msg = "The user has insufficient permissions to access this document."
            raise PermissionDenied(error_msg)

    def filter_documenten_for_permissions(
        self,
        documenten: List[Document],
        user: User,
    ) -> List[Document]:
        """Filter documents on the user permissions. """

        filtered_documenten = []
        for document in documenten:
            try:
                self.check_document_permissions(document, user)
                filtered_documenten.append(document)
            except PermissionDenied:
                continue

        return filtered_documenten
