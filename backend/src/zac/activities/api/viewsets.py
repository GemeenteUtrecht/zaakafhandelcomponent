from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import exceptions, mixins, permissions, viewsets
from rest_framework.response import Response
from zgw_consumers.concurrent import parallel

from zac.core.services import get_document, get_zaak

from ..models import Activity, Event
from .filters import ActivityFilter
from .permissions import CanReadZaakPermission, CanWritePermission
from .serializers import ActivitySerializer, EventSerializer, PatchActivitySerializer


@extend_schema_view(
    list=extend_schema(
        summary=_("List activities"),
        parameters=[
            OpenApiParameter(
                name="zaak",
                required=True,
                type=OpenApiTypes.URI,
                description=_("The url of the case related to the activities."),
                location=OpenApiParameter.QUERY,
            )
        ],
    ),
    retrieve=extend_schema(summary=_("Retrieve activity")),
    create=extend_schema(summary=_("Create activity")),
    update=extend_schema(
        summary=_("Update activity"),
        request=PatchActivitySerializer,
        response=ActivitySerializer,
    ),
    destroy=extend_schema(summary=_("Destroy activity")),
    tags=["activities"],
)
class ActivityViewSet(viewsets.ModelViewSet):
    queryset = (
        Activity.objects.order_by("created")
        .select_related("assignee")
        .prefetch_related(
            Prefetch("events", queryset=Event.objects.order_by("created"))
        )
    )
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaakPermission | CanWritePermission,
    )
    serializer_class = ActivitySerializer
    filterset_class = ActivityFilter

    def get_serializer(self, **kwargs):
        if self.request.method == "PATCH":
            return PatchActivitySerializer(**kwargs)
        return super().get_serializer(**kwargs)

    # Set document for document serializer
    def get_queryset(self):
        queryset = super().get_queryset()
        document_urls = {
            activity.document for activity in queryset if activity.document
        }
        with parallel() as executor:
            result = executor.map(get_document, document_urls)
        documents = {document.url: document for document in list(result)}
        for activity in queryset:
            activity.document = documents[activity.document]
        return queryset

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        if self.action == "list":
            # for permission reasons, don't allow data retrieval without 'zaak' filter
            zaak_url = self.request.query_params.get("zaak")
            if not zaak_url:
                return queryset.none()

            # permission check on the zaak itself
            zaak = get_zaak(zaak_url=zaak_url)
            if not self.request.user.has_perm("activities:read", zaak):
                raise exceptions.PermissionDenied(
                    "Not allowed to read activities for this zaak."
                )

        return qs

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance=instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        serializer = self.serializer_class(instance=self.get_object())
        return Response(serializer.data)


@extend_schema_view(
    create=extend_schema(summary=_("Create event")),
)
class EventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Event.objects.none()
    serializer_class = EventSerializer
    permission_classes = (permissions.IsAuthenticated, CanWritePermission)
