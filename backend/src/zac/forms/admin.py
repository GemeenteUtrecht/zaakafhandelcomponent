from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import FormsConfig


@admin.register(FormsConfig)
class FormsConfigAdmin(SingletonModelAdmin):
    pass
