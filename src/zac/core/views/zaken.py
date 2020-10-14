from itertools import chain, groupby
from typing import Any, Dict, List, Optional

from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView

from extra_views import ModelFormSetView
from furl import furl
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.concurrent import parallel

from zac.accounts.mixins import PermissionRequiredMixin
from zac.accounts.models import AccessRequest
from zac.accounts.permissions import UserPermissions
from zac.activities.constants import ActivityStatuses
from zac.activities.models import Activity
from zac.contrib.kownsl.api import (
    get_review_requests,
    retrieve_advices,
    retrieve_approvals,
)
from zac.contrib.kownsl.data import ReviewRequest
from zac.utils.api_models import serialize

from ..base_views import BaseDetailView, BaseListView, SingleObjectMixin
from ..forms import (
    AccessRequestCreateForm,
    AccessRequestHandleForm,
    BaseAccessRequestFormSet,
    ZaakAfhandelForm,
    ZakenFilterForm,
)
from ..permissions import (
    zaken_close,
    zaken_handle_access,
    zaken_inzien,
    zaken_request_access,
    zaken_set_result,
)
from ..services import (
    find_zaak,
    get_document,
    get_documenten,
    get_related_zaken,
    get_resultaat,
    get_rollen,
    get_statussen,
    get_zaak_eigenschappen,
    get_zaakobjecten,
    get_zaaktypen,
    get_zaken,
)
from ..zaakobjecten import GROUPS, ZaakObjectGroup
from .mixins import DocumentPermissionMixin
from .utils import get_zaak_from_query


class Index(PermissionRequiredMixin, BaseListView):
    """
    Display the landing screen.

    The list of zaken that can be viewed is retrieved from the APIs.

    Note that permission checks are in place - only zaken of zaaktypen are retrieved
    where you have access to the zaaktype.
    """

    template_name = "core/index.html"
    context_object_name = "zaken"
    filter_form_class = ZakenFilterForm
    permission_required = zaken_inzien.name

    def get_filter_form_kwargs(self):
        kwargs = super().get_filter_form_kwargs()
        kwargs["zaaktypen"] = get_zaaktypen(UserPermissions(self.request.user))
        return kwargs

    def get_object_list(self):
        filter_form = self.get_filter_form()
        if filter_form.is_valid():
            filters = filter_form.as_filters()
        else:
            filters = {}
        user_perms = UserPermissions(self.request.user)
        zaken = get_zaken(user_perms, **filters)[:50]

        return zaken


class ZaakDetail(PermissionRequiredMixin, DocumentPermissionMixin, BaseDetailView):
    template_name = "core/zaak_detail.html"
    context_object_name = "zaak"
    permission_required = zaken_inzien.name

    def get_object(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        with parallel() as executor:
            _related_zaken = executor.submit(get_related_zaken, self.object)
            _review_requests = executor.submit(get_review_requests, self.object)

            review_requests = _review_requests.result()

            _advices = executor.map(
                lambda rr: retrieve_advices(rr) if rr else [],
                [rr if rr.num_advices else None for rr in review_requests],
            )
            _approvals = executor.map(
                lambda rr: retrieve_approvals(rr) if rr else [],
                [rr if rr.num_approvals else None for rr in review_requests],
            )

            related_zaken = _related_zaken.result()

            for rr, rr_advices, rr_approvals in zip(
                review_requests, _advices, _approvals
            ):
                rr.advices = rr_advices
                rr.approvals = rr_approvals

        # get the advice versions - the minimal versions are needed
        # for the documents table
        doc_versions = self.get_source_doc_versions(review_requests)
        self._set_advice_documents(review_requests)

        with parallel() as executor:
            statussen = executor.submit(get_statussen, self.object)
            _documenten = executor.submit(get_documenten, self.object, doc_versions)
            eigenschappen = executor.submit(get_zaak_eigenschappen, self.object)
            rollen = executor.submit(get_rollen, self.object)

            resultaat = executor.submit(get_resultaat, self.object)

            documenten, gone = _documenten.result()

            filtered_documenten = self.filter_documenten_for_permissions(
                documenten, self.request.user
            )

            review_requests = serialize(review_requests)

            context.update(
                {
                    "statussen": statussen.result(),
                    "documenten": filtered_documenten,
                    "documenten_gone": gone,
                    "eigenschappen": eigenschappen.result(),
                    "resultaat": resultaat.result(),
                    "related_zaken": related_zaken,
                    "rollen": rollen.result(),
                    "review_requests": review_requests,
                }
            )

        context.update(
            {
                "activity_count": Activity.objects.filter(
                    zaak=self.object.url, status=ActivityStatuses.on_going
                ).count()
            }
        )

        return context

    @staticmethod
    def get_source_doc_versions(
        review_requests: List[ReviewRequest],
    ) -> Optional[Dict[str, int]]:
        advices = list(chain(*[rr.advices for rr in review_requests if rr.advices]))
        all_documents = sum((advice.documents for advice in advices), [])
        sort_key = lambda ad: ad.document  # noqa
        all_documents = sorted(all_documents, key=sort_key)
        doc_versions = {
            document_url: min(doc.source_version for doc in docs)
            for document_url, docs in groupby(all_documents, key=sort_key)
        }
        return doc_versions

    @staticmethod
    def _set_advice_documents(review_requests: List[ReviewRequest]):
        _document_versions = set()

        for review_request in review_requests:
            for advice in review_request.advices:
                for document_advice in advice.documents:
                    source_version = furl(document_advice.document)
                    source_version.args["versie"] = document_advice.source_version
                    _document_versions.add(source_version.url)

                    advice_version = furl(document_advice.document)
                    advice_version.args["versie"] = document_advice.advice_version
                    _document_versions.add(advice_version.url)

        document_versions = list(_document_versions)

        with parallel() as executor:
            results = executor.map(get_document, document_versions)

        versioned_documents = {
            (document.url, document.versie): document for document in results
        }

        for review_request in review_requests:
            for advice in review_request.advices:
                _docs = []
                for document_advice in advice.documents:
                    source_key, advice_key = (
                        (document_advice.document, document_advice.source_version),
                        (document_advice.document, document_advice.advice_version),
                    )

                    _docs.append(
                        {
                            "source": versioned_documents[source_key],
                            "advice": versioned_documents[advice_key],
                        }
                    )

                advice.documents = _docs


class FetchZaakObjecten(PermissionRequiredMixin, TemplateView):
    """
    Retrieve the ZaakObjecten for a given zaak reference.

    Intended to be called via AJAX.
    """

    template_name = "core/includes/zaakobjecten.html"
    permission_required = zaken_inzien.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        zaak = get_zaak_from_query(self.request)
        self.check_object_permissions(zaak)

        context["zaakobjecten"] = self._get_zaakobjecten(zaak)

        return context

    def _get_zaakobjecten(self, zaak: Zaak) -> List[ZaakObjectGroup]:
        # API call
        zaakobjecten = get_zaakobjecten(zaak.url)

        def group_key(zo):
            if zo.object_type == "overige":
                return zo.object_type_overige
            return zo.object_type

        # re-group by type
        render_groups = []
        zaakobjecten = sorted(zaakobjecten, key=group_key)
        grouped = groupby(zaakobjecten, key=group_key)
        for _group, items in grouped:
            group = GROUPS.get(_group, ZaakObjectGroup(label=_group))
            group.retrieve_items(items)
            render_groups.append(group)
        return render_groups


class ZaakAfhandelView(PermissionRequiredMixin, SingleObjectMixin, FormView):
    form_class = ZaakAfhandelForm
    template_name = "core/zaak_afhandeling.html"
    context_object_name = "zaak"
    permission_required = "zaken:afhandelen"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_object(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        return context

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()

        user = self.request.user
        can_set_result = user.has_perm(zaken_set_result.name, self.object)
        can_close = user.has_perm(zaken_close.name, self.object)

        return {
            "zaak": self.object,
            "can_set_result": can_set_result,
            "can_close": can_close,
            **kwargs,
        }

    def form_valid(self, form: ZaakAfhandelForm):
        form.save(user=self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("core:zaak-detail", kwargs=self.kwargs)


class ZaakActiviteitenView(PermissionRequiredMixin, BaseDetailView):
    template_name = "core/zaak_activiteiten.html"
    context_object_name = "zaak"
    permission_required = zaken_inzien.name

    def get_object(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak


class AccessRequestCreateView(PermissionRequiredMixin, FormView):
    form_class = AccessRequestCreateForm
    template_name = "core/create_access_request.html"
    #  todo add thanks page?
    success_url = reverse_lazy("core:index")
    permission_required = zaken_request_access.name

    def get_zaak(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs["requester"] = self.request.user
        kwargs["zaak"] = self.get_zaak()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"zaak": self.get_zaak()})
        return context

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ZaakAccessRequestsView(PermissionRequiredMixin, ModelFormSetView):
    form_class = AccessRequestHandleForm
    formset_class = BaseAccessRequestFormSet
    template_name = "core/zaak_access_requests.html"
    context_object_name = "zaak"
    model = AccessRequest
    factory_kwargs = {"extra": 0, "can_delete": False}
    permission_required = zaken_handle_access.name

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(result="", zaak=self.zaak.url)
        return queryset

    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()

        form_kwargs = kwargs.pop("form_kwargs", {})
        form_kwargs["request"] = self.request
        kwargs["form_kwargs"] = form_kwargs

        return kwargs

    def get_zaak(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak

    @property
    def zaak(self):
        if not hasattr(self, "_zaak"):
            self._zaak = self.get_zaak()
        return self._zaak

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "zaak": self.zaak,
                "access_requests": (
                    AccessRequest.objects.select_related("requester", "handler")
                    .filter(zaak=self.zaak.url)
                    .exclude(result="")
                ),
            }
        )
        return context
