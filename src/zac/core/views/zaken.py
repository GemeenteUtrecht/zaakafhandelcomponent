from concurrent import futures
from itertools import groupby
from typing import Any, Dict, List, Optional

from django.urls import reverse
from django.views.generic import FormView, TemplateView

from furl import furl
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.mixins import PermissionRequiredMixin
from zac.accounts.permissions import UserPermissions
from zac.contrib.kownsl.api import (
    get_review_requests,
    retrieve_advice_collection,
    retrieve_approval_collection,
)
from zac.contrib.kownsl.data import AdviceCollection

from ..base_views import BaseDetailView, BaseListView, SingleObjectMixin
from ..forms import ZaakAfhandelForm, ZakenFilterForm
from ..permissions import zaken_close, zaken_inzien, zaken_set_result
from ..services import (
    find_zaak,
    get_document,
    get_documenten,
    get_related_zaken,
    get_resultaat,
    get_rollen,
    get_statussen,
    get_zaak,
    get_zaak_eigenschappen,
    get_zaakobjecten,
    get_zaaktypen,
    get_zaken,
)
from ..zaakobjecten import GROUPS, ZaakObjectGroup
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


class ZaakDetail(PermissionRequiredMixin, BaseDetailView):
    template_name = "core/zaak_detail.html"
    context_object_name = "zaak"
    permission_required = zaken_inzien.name

    def get_object(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        with futures.ThreadPoolExecutor() as executor:
            _advice_collection = executor.submit(
                retrieve_advice_collection, self.object
            )
            _approval_collection = executor.submit(
                retrieve_approval_collection, self.object
            )
            _related_zaken = executor.submit(get_related_zaken, self.object)
            _review_requests = executor.submit(get_review_requests, self.object)

            advice_collection = _advice_collection.result()
            approval_collection = _approval_collection.result()
            related_zaken = _related_zaken.result()
            review_requests = _review_requests.result()

            # fetch the review cases
            _review_zaken = executor.map(
                lambda url: get_zaak(zaak_url=url) if url else None,
                [review_request.review_zaak for review_request in review_requests],
            )
            for review_zaak, review_request in zip(_review_zaken, review_requests):
                review_request.review_zaak = review_zaak

        # get the advice versions - the minimal versions are needed
        # for the documents table
        doc_versions = self.get_source_doc_versions(advice_collection)

        with futures.ThreadPoolExecutor() as executor:
            statussen = executor.submit(get_statussen, self.object)
            _documenten = executor.submit(get_documenten, self.object, doc_versions)
            eigenschappen = executor.submit(get_zaak_eigenschappen, self.object)
            rollen = executor.submit(get_rollen, self.object)

            resultaat = executor.submit(get_resultaat, self.object)

            documenten, gone = _documenten.result()

            if advice_collection:
                _get_zaak = executor.submit(
                    get_zaak, zaak_url=advice_collection.for_zaak
                )
                advice_collection.for_zaak = _get_zaak.result()

            context.update(
                {
                    "statussen": statussen.result(),
                    "documenten": documenten,
                    "documenten_gone": gone,
                    "eigenschappen": eigenschappen.result(),
                    "resultaat": resultaat.result(),
                    "related_zaken": related_zaken,
                    "rollen": rollen.result(),
                    "advice_collection": advice_collection,
                    "approval_collection": approval_collection,
                    "review_requests": review_requests,
                }
            )
        self._set_advice_documents(advice_collection, documenten)
        return context

    @staticmethod
    def get_source_doc_versions(
        advice_collection: Optional[AdviceCollection],
    ) -> Optional[Dict[str, int]]:
        if advice_collection is None:
            return None

        all_documents = sum(
            (advice.documents for advice in advice_collection.advices), []
        )
        sort_key = lambda ad: ad.document  # noqa
        all_documents = sorted(all_documents, key=sort_key)
        doc_versions = {
            document_url: min(doc.source_version for doc in docs)
            for document_url, docs in groupby(all_documents, key=sort_key)
        }
        return doc_versions

    @staticmethod
    def _set_advice_documents(
        advice_collection: Optional[AdviceCollection], documents: List[Document]
    ):
        if advice_collection is None:
            return

        _document_versions = set()
        advices = advice_collection.advices

        for advice in advices:
            for document_advice in advice.documents:
                source_version = furl(document_advice.document)
                source_version.args["versie"] = document_advice.source_version
                _document_versions.add(source_version.url)

                advice_version = furl(document_advice.document)
                advice_version.args["versie"] = document_advice.advice_version
                _document_versions.add(advice_version.url)

        document_versions = list(_document_versions)

        with futures.ThreadPoolExecutor() as executor:
            results = executor.map(get_document, document_versions)

        versioned_documents = {
            (document.url, document.versie): document for document in results
        }

        for advice in advices:
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
