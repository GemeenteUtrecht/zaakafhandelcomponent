from typing import List

from django.core.exceptions import PermissionDenied
from django.db.models import Q

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document

from zac.accounts.models import InformatieobjecttypePermission, PermissionSet, User


class DocumentPermissionMixin:
    @staticmethod
    def check_document_permissions(document: Document, user: User):
        """Check if a user has the permission to see a document"""
        error_msg = "The user has insufficient permissions to access this document."

        user_permissions = PermissionSet.objects.filter(
            authorizationprofile__in=user.auth_profiles.all()
        )

        if not user_permissions.exists():
            raise PermissionDenied(error_msg)

        relevant_iot_permissions = InformatieobjecttypePermission.objects.filter(
            catalogus=document.informatieobjecttype.catalogus
        )

        user_iot_permissions = relevant_iot_permissions.filter(
            permission_set__in=user_permissions
        )

        if not user_iot_permissions.exists():
            raise PermissionDenied(error_msg)

        # The user has permissions to the catalog in question.
        # Now need to check whether they have the right confidentiality level

        document_va = VertrouwelijkheidsAanduidingen.get_choice(
            document.informatieobjecttype.vertrouwelijkheidaanduiding
        ).order

        order_case = VertrouwelijkheidsAanduidingen.get_order_expression("max_va")

        confidentiality_permissions = user_iot_permissions.annotate(
            max_va_order=order_case
        ).filter(max_va_order__gte=document_va)

        if not confidentiality_permissions.exists():
            raise PermissionDenied(error_msg)

        # If there is no omschrijving specified in the remaining permissions, then the user has access.
        # Otherwise need to check that the user has permissions for the specific omschrijving.

        required_permission = confidentiality_permissions.filter(
            Q(omschrijving=document.informatieobjecttype.omschrijving)
            | Q(omschrijving="")
        )

        if not required_permission.exists():
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
