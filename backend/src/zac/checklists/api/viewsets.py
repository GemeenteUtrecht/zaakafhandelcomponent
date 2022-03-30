from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, permissions, viewsets
from rest_framework.generics import get_object_or_404

from zac.core.services import find_zaak
from zgw.models.zrc import Zaak

from ..models import Checklist, ChecklistAnswer, ChecklistQuestion, ChecklistType
from .permissions import (
    CanReadOrWriteChecklistsPermission,
    CanReadZaakChecklistTypePermission,
)
from .serializers import (
    ChecklistSerializer,
    ChecklistTypeSerializer,
    ReadChecklistSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary=_("List checklisttype and related questions."),
        parameters=[
            OpenApiParameter(
                name="zaak",
                required=True,
                type=OpenApiTypes.URI,
                description=_(
                    "URL-reference of the ZAAK with ZAAKTYPE related to the checklisttype."
                ),
                location=OpenApiParameter.QUERY,
            )
        ],
    ),
    retrieve=extend_schema(summary=_("Retrieve checklisttype and related questions.")),
    create=extend_schema(summary=_("Create checklisttype and related questions.")),
    update=extend_schema(summary=_("Update checklisttype and related questions.")),
)
class ChecklistTypeViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ChecklistType.objects.prefetch_related(
        Prefetch(
            "checklistquestion_set",
            queryset=ChecklistQuestion.objects.prefetch_related(
                "questionchoice_set"
            ).all(),
        )
    ).all()
    permission_classes = (
        permissions.IsAuthenticated,
        permissions.IsAdminUser,
    )
    http_method_names = [
        "get",
        "post",
        "put",
    ]
    serializer_class = ChecklistTypeSerializer


@extend_schema_view(
    retrieve=extend_schema(
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
    ),
)
class ZaakChecklistTypeViewSet(
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ChecklistType.objects.prefetch_related(
        Prefetch(
            "checklistquestion_set",
            queryset=ChecklistQuestion.objects.prefetch_related(
                "questionchoice_set"
            ).all(),
        )
    ).all()
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaakChecklistTypePermission,
    )
    serializer_class = ChecklistTypeSerializer

    def get_object(self) -> ChecklistType:
        queryset = self.filter_queryset(self.get_queryset())
        bronorganisatie = self.request.parser_context["kwargs"]["bronorganisatie"]
        identificatie = self.request.parser_context["kwargs"]["identificatie"]
        zaak = find_zaak(bronorganisatie, identificatie)
        filter_kwargs = {
            "zaaktype_omschrijving": zaak.zaaktype.omschrijving,
            "zaaktype_catalogus": zaak.zaaktype.catalogus,
        }
        checklist_type = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, zaak)
        return checklist_type


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


@extend_schema_view(
    retrieve=extend_schema(
        summary=_("Retrieve checklist and related answers."),
        parameters=zaak_checklist_parameters,
    ),
    create=extend_schema(
        summary=_("Create checklist and related answers."),
        parameters=zaak_checklist_parameters,
    ),
    update=extend_schema(
        summary=_("Update checklist and related answers."),
        parameters=zaak_checklist_parameters,
    ),
)
class ZaakChecklistViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        Checklist.objects.select_related("checklist_type")
        .select_related("user_assignee")
        .select_related("group_assignee")
        .select_related("checklist_type")
        .prefetch_related(
            Prefetch("checklistanswer_set", queryset=ChecklistAnswer.objects.all())
        )
        .all()
    )
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrWriteChecklistsPermission,
    )
    http_method_names = [
        "get",
        "post",
        "put",
    ]
    serializer_class = ChecklistSerializer

    def get_serializer_class(self):
        mapping = {
            "GET": ReadChecklistSerializer,
            "POST": ChecklistSerializer,
            "PUT": ChecklistSerializer,
        }
        return mapping[self.request.method]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["zaak"] = self.get_zaak()
        return context

    def get_zaak(self) -> Zaak:
        bronorganisatie = self.request.parser_context["kwargs"]["bronorganisatie"]
        identificatie = self.request.parser_context["kwargs"]["identificatie"]
        zaak = find_zaak(bronorganisatie, identificatie)
        return zaak

    def get_object(self) -> ChecklistType:
        queryset = self.filter_queryset(self.get_queryset())
        zaak = self.get_zaak()
        filter_kwargs = {
            "zaak": zaak.url,
        }
        checklist = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, checklist)
        return checklist
