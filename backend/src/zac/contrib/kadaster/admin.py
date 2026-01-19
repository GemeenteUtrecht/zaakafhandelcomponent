from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import KadasterConfig


@admin.register(KadasterConfig)
class KadasterConfigAdmin(SingletonModelAdmin):
    pass
