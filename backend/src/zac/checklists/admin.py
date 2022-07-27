from django.contrib import admin

from nested_admin import (
    NestedModelAdminMixin,
    NestedTabularInline,
    NestedTabularInlineMixin,
)
from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedTabularInline

from .forms import ChecklistTypeForm
from .models import Checklist, ChecklistQuestion, ChecklistType, QuestionChoice


class QuestionChoiceAdmin(NestedTabularInline):
    list_display = ("question", "name", "value")
    date_hierarchy = "created"
    autocomplete_fields = ("question",)
    model = QuestionChoice
    extra = 0


class ChecklistQuestionAdmin(NestedTabularInlineMixin, OrderedTabularInline):
    fields = (
        "question",
        "move_up_down_links",
    )
    readonly_fields = ("move_up_down_links",)
    search_fields = ("question",)
    inlines = [QuestionChoiceAdmin]
    model = ChecklistQuestion
    extra = 0
    ordering = ["order"]


class ChecklistTypeAdmin(
    OrderedInlineModelAdminMixin, NestedModelAdminMixin, admin.ModelAdmin
):
    list_display = ("zaaktype_identificatie", "zaaktype_catalogus")
    list_filter = ("zaaktype_identificatie",)
    search_fields = ("zaaktype_identificatie",)
    date_hierarchy = "created"
    form = ChecklistTypeForm
    inlines = [ChecklistQuestionAdmin]
    extra = 0


admin.site.register(ChecklistType, ChecklistTypeAdmin)


@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = (
        "zaak",
        "checklisttype",
    )
    list_filter = ("checklisttype",)
    date_hierarchy = "created"
