from django.contrib import admin

from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin

from .models import SearchReport


@admin.register(SearchReport)
class SearchReportAdmin(DynamicArrayMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "fields",
        "query",
    )
