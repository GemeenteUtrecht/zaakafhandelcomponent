from django.contrib import admin

from .models import OrganisatieOnderdeel


@admin.register(OrganisatieOnderdeel)
class OrganisatieOnderdeelAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
