from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import DowcConfig


@admin.register(DowcConfig)
class DowcConfigAdmin(SingletonModelAdmin):
    pass
