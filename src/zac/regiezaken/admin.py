from django.contrib import admin

from zgw_consumers.admin import ListZaaktypenMixin

from .models import RegieZaakConfiguratie


@admin.register(RegieZaakConfiguratie)
class RegieZaakConfiguratieAdmin(ListZaaktypenMixin, admin.ModelAdmin):
    list_display = ("name",)
    zaaktype_fields = ("zaaktype_main",)
