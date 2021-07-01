from django.contrib import admin

from .models import SearchReport


@admin.register(SearchReport)
class SearchReportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "query",
    )
