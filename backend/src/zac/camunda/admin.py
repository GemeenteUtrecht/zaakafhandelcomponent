from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import BPTLAppId


@admin.register(BPTLAppId)
class BPTLAppIdAdmin(SingletonModelAdmin):
    pass
