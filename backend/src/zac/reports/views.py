from io import BytesIO

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import FileResponse
from django.views import View
from django.views.generic import ListView
from django.views.generic.detail import SingleObjectMixin

from zac.core.services import get_zaaktypen

from .export import export_zaken
from .models import Report


class ReportsListView(LoginRequiredMixin, ListView):
    model = Report
    context_object_name = "reports"

    def get_queryset(self):
        qs = super().get_queryset()

        # filter on allowed zaaktypen
        zaaktypen = get_zaaktypen(self.request.user)
        identificaties = list({zt.identificatie for zt in zaaktypen})

        # only allow reports where the zaaktypen are a sub-set of the accessible zaaktypen
        # for this particular user
        return qs.filter(zaaktypen__contained_by=identificaties)


class DownloadReportView(
    LoginRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, View
):
    model = Report

    def has_permission(self):
        # move logic from "reports:download" rule
        report = self.get_object()
        if not report:
            return True

        zaaktypen = get_zaaktypen(self.request.user)
        identificaties = {zt.identificatie for zt in zaaktypen}
        return set(report.zaaktypen).issubset(identificaties)

    def get(self, request, *args, **kwargs):
        report = self.get_object()

        dataset = export_zaken(report)

        response = FileResponse(
            BytesIO(dataset.export("xlsx")),
            as_attachment=True,
            filename=f"{report.name}.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return response
