from typing import Dict, List

from django.http import Http404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, views
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from zac.contrib.objects.cache import invalidate_cache_fetch_checklist_object
from zac.contrib.objects.services import (
    fetch_checklist,
    fetch_checklist_object,
    fetch_checklisttype,
)
from zac.core.api.permissions import CanForceEditClosedZaken
from zac.core.services import find_zaak, update_object_record_data
from zgw.models.zrc import Zaak

from ..data import Checklist, ChecklistAnswer, ChecklistType
from .permission_loaders import add_permissions_for_checklist_assignee
from .permissions import (
    CanReadOrWriteChecklistsPermission,
    CanReadZaakChecklistTypePermission,
    ChecklistIsLockedByCurrentUser,
)
from .serializers import ChecklistSerializer, ChecklistTypeSerializer

zaak_checklist_parameters = [
    OpenApiParameter(
        name="bronorganisatie",
        required=True,
        type=OpenApiTypes.STR,
        description=_(
            "Bronorganisatie of the ZAAK with ZAAKTYPE related to the checklisttype."
        ),
        location=OpenApiParameter.PATH,
    ),
    OpenApiParameter(
        name="identificatie",
        required=True,
        type=OpenApiTypes.STR,
        description=_(
            "Identificatie of the ZAAK with ZAAKTYPE related to the checklisttype."
        ),
        location=OpenApiParameter.PATH,
    ),
]


class ZaakChecklistTypeView(views.APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaakChecklistTypePermission,
    )
    serializer_class = ChecklistTypeSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get_object(self) -> ChecklistType:
        bronorganisatie = self.request.parser_context["kwargs"]["bronorganisatie"]
        identificatie = self.request.parser_context["kwargs"]["identificatie"]
        zaak = find_zaak(bronorganisatie, identificatie)
        if not (checklisttype := fetch_checklisttype(zaak.zaaktype)):
            raise Http404("Checklisttype not found for ZAAK.")

        self.check_object_permissions(self.request, zaak)
        return checklisttype

    @extend_schema(
        summary=_("Retrieve checklisttype and related questions for ZAAK."),
        parameters=zaak_checklist_parameters,
    )
    def get(self, request, *args, **kwargs):
        checklisttype = self.get_object()
        return Response(self.get_serializer(checklisttype).data)


class BaseZaakChecklistView(views.APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        CanReadOrWriteChecklistsPermission,
        ChecklistIsLockedByCurrentUser,
        CanForceEditClosedZaken,
    ]
    serializer_class = ChecklistSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get_zaak(self) -> Zaak:
        if not hasattr(self, "_zaak"):
            bronorganisatie = self.request.parser_context["kwargs"]["bronorganisatie"]
            identificatie = self.request.parser_context["kwargs"]["identificatie"]
            self._zaak = find_zaak(bronorganisatie, identificatie)
        return self._zaak

    def get_checklist_object(self) -> Dict:
        if not hasattr(self, "_checklist_object"):
            if not (checklist_object := fetch_checklist_object(self.get_zaak())):
                raise Http404("Checklist not found for ZAAK.")
            self._checklist_object = checklist_object
        return self._checklist_object

    def get_object(self) -> Checklist:
        zaak = self.get_zaak()
        self.check_object_permissions(self.request, zaak)
        checklist_object = self.get_checklist_object()
        if not hasattr(self, "_checklist"):
            self._checklist = fetch_checklist(
                zaak, checklist_object_data=checklist_object
            )
        return self._checklist


class ZaakChecklistView(BaseZaakChecklistView):
    def _add_permissions_for_checklist_assignee(
        self, zaak, answers: List[ChecklistAnswer]
    ):
        for answer in answers:
            if answer.user_assignee:
                add_permissions_for_checklist_assignee(zaak, answer.user_assignee)
            if answer.group_assignee:
                users = answer.group_assignee.user_set.all()
                for user in users:
                    add_permissions_for_checklist_assignee(zaak, user)

    @extend_schema(
        summary=_("Retrieve checklist and related answers."),
        parameters=zaak_checklist_parameters,
        responses={200: ChecklistSerializer},
    )
    def get(self, request, *args, **kwargs):
        checklist = self.get_object()
        serializer = self.get_serializer(instance=checklist)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Create checklist and related answers."),
        parameters=zaak_checklist_parameters,
        responses={201: ChecklistSerializer},
    )
    def post(self, request, *args, **kwargs):
        # Permission check
        zaak = self.get_zaak()
        self.check_object_permissions(request, zaak)
        # Serialize and create object
        serializer = self.get_serializer(
            data=request.data,
            context={
                "request": self.request,
                "view": self,
                "zaak": zaak,
            },
        )
        serializer.is_valid(raise_exception=True)
        checklist = serializer.create()

        # Add permissions:
        self._add_permissions_for_checklist_assignee(zaak, checklist.answers)

        invalidate_cache_fetch_checklist_object(zaak)
        return Response(
            self.get_serializer(checklist).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary=_("Update checklist and related answers."),
        parameters=zaak_checklist_parameters,
        responses={200: ChecklistSerializer},
    )
    def put(self, request, *args, **kwargs):
        zaak = self.get_zaak()
        checklist = self.get_object()
        serializer = self.get_serializer(
            instance=checklist,
            data=request.data,
            context={
                "request": self.request,
                "view": self,
                "zaak": zaak,
                "checklist_object": self.get_checklist_object(),
            },
        )
        serializer.is_valid(raise_exception=True)
        checklist = serializer.update()
        self._add_permissions_for_checklist_assignee(zaak, checklist.answers)
        invalidate_cache_fetch_checklist_object(self.get_zaak())
        return Response(self.get_serializer(checklist).data, status=status.HTTP_200_OK)


class LockZaakChecklistView(BaseZaakChecklistView):
    @extend_schema(
        summary=_("Lock a checklist."),
        parameters=zaak_checklist_parameters,
        request=None,
        responses={204: None},
    )
    def post(self, request, *args, **kwargs):
        self.get_object()  # check permissions
        checklist_obj = self.get_checklist_object()
        if checklist_obj["record"]["data"]["lockedBy"]:
            raise ValidationError(_("Checklist is already locked."))

        checklist_obj["record"]["data"]["lockedBy"] = request.user.username
        update_object_record_data(
            object=checklist_obj,
            data=checklist_obj["record"]["data"],
            user=request.user,
        )
        invalidate_cache_fetch_checklist_object(self.get_zaak())
        return Response(status=status.HTTP_204_NO_CONTENT)


class UnlockZaakChecklistView(BaseZaakChecklistView):
    @extend_schema(
        summary=_("Unlock a checklist."),
        parameters=zaak_checklist_parameters,
        request=None,
        responses={204: None},
    )
    def post(self, request, *args, **kwargs):
        self.get_object()  # check permissions
        checklist_obj = self.get_checklist_object()
        if not checklist_obj["record"]["data"]["lockedBy"]:
            raise ValidationError(_("Checklist is not locked."))
        checklist_obj["record"]["data"]["lockedBy"] = None
        update_object_record_data(
            object=checklist_obj,
            data=checklist_obj["record"]["data"],
            user=request.user,
        )
        invalidate_cache_fetch_checklist_object(self.get_zaak())
        return Response(status=status.HTTP_204_NO_CONTENT)
