from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import exceptions, mixins, permissions, viewsets

from zac.core.services import get_zaak, get_zaaktype

from ..models import Checklist, ChecklistAnswer, ChecklistQuestion, ChecklistType
from .filters import ChecklistFilter
from .permissions import (
    CanReadOrWriteChecklistsPermission,
    CanReadOrWriteChecklistTypePermission,
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
        CanReadOrWriteChecklistTypePermission,
    )
    http_method_names = [
        "get",
        "post",
        "put",
    ]
    serializer_class = ChecklistTypeSerializer

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        if self.action == "list":
            zaak = get_zaak(zaak_url=self.request.GET.get("zaak"))
            zaaktype = get_zaaktype(zaak.zaaktype)
            qs = qs.filter(
                zaaktype_omschrijving=zaaktype.omschrijving,
                zaaktype_catalogus=zaaktype.catalogus,
            )
        return qs

    def list(self, request, *args, **kwargs):
        if not request.GET.get("zaak"):
            raise exceptions.ValidationError(_("Missing the `zaak` query parameter."))

        return super().list(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(
        summary=_("List checklist and related answers."),
        parameters=[
            OpenApiParameter(
                name="zaak",
                required=True,
                type=OpenApiTypes.URI,
                description=_("URL-reference of the ZAAK related to the checklist."),
                location=OpenApiParameter.QUERY,
            )
        ],
    ),
    create=extend_schema(summary=_("Create checklist and related answers.")),
    update=extend_schema(
        summary=_("Update checklist and related answers."),
    ),
)
class ChecklistViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
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
    filterset_class = ChecklistFilter
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

    def list(self, request, *args, **kwargs):
        if not request.GET.get("zaak"):
            raise exceptions.ValidationError(_("Missing the `zaak` query parameter."))

        return super().list(request, *args, **kwargs)
