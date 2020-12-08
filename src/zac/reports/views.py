from io import BytesIO

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
from django.views import View
from django.views.generic.detail import SingleObjectMixin

from .export import export_zaken
from .models import Report


class DownloadReportView(LoginRequiredMixin, SingleObjectMixin, View):
    model = Report

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
