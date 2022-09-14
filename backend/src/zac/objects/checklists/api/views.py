from typing import List

from django.http import Http404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, views
from rest_framework.response import Response

from zac.core.api.permissions import CanForceEditClosedZaken
from zac.core.services import find_zaak
from zac.objects.services import fetch_checklist, fetch_checklisttype
from zgw.models.zrc import Zaak

from ..data import Checklist, ChecklistAnswer, ChecklistType
from .permission_loaders import add_permissions_for_checklist_assignee
from .permissions import (
    CanReadOrWriteChecklistsPermission,
    CanReadZaakChecklistTypePermission,
)
from .serializers import ChecklistSerializer, ChecklistTypeSerializer


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
        parameters=[
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
        ],
    )
    def get(self, request, *args, **kwargs):
        checklisttype = self.get_object()
        return Response(self.get_serializer(checklisttype).data)


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


class ZaakChecklistView(views.APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrWriteChecklistsPermission,
        CanForceEditClosedZaken,
    )
    serializer_class = ChecklistSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get_zaak(self) -> Zaak:
        bronorganisatie = self.request.parser_context["kwargs"]["bronorganisatie"]
        identificatie = self.request.parser_context["kwargs"]["identificatie"]
        zaak = find_zaak(bronorganisatie, identificatie)
        return zaak

    def get_object(self) -> Checklist:
        zaak = self.get_zaak()
        self.check_object_permissions(self.request, zaak)
        if not (checklist := fetch_checklist(zaak)):
            raise Http404("Checklist not found for ZAAK.")
        return checklist

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
        responses={"200": ChecklistSerializer},
    )
    def get(self, request, *args, **kwargs):
        checklist = self.get_object()
        serializer = self.get_serializer(instance=checklist)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Create checklist and related answers."),
        parameters=zaak_checklist_parameters,
        responses={"201": ChecklistSerializer},
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
        return Response(
            self.get_serializer(checklist).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary=_("Update checklist and related answers."),
        parameters=zaak_checklist_parameters,
        responses={"200": ChecklistSerializer},
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
            },
        )
        serializer.is_valid(raise_exception=True)
        checklist = serializer.update()
        self._add_permissions_for_checklist_assignee(zaak, checklist.answers)
        return Response(self.get_serializer(checklist).data, status=status.HTTP_200_OK)
