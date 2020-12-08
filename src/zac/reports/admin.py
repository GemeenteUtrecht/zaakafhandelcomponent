from django.contrib import admin

from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin

from .models import Report


@admin.register(Report)
class ReportAdmin(DynamicArrayMixin, admin.ModelAdmin):
    list_display = ("name", "zaaktypen")
