from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('label', 'api_type', 'api_root')
    list_filter = ('api_type',)
    search_fields = ('label', 'api_root')
