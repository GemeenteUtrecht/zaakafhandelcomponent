from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import DocConfig


@admin.register(DocConfig)
class DocConfigAdmin(SingletonModelAdmin):
    pass
