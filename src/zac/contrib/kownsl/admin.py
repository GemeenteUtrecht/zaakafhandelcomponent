from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import KownslConfig


@admin.register(KownslConfig)
class KownslConfigAdmin(SingletonModelAdmin):
    pass
