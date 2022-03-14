from django.contrib import admin

from nested_admin import NestedModelAdmin, NestedStackedInline, NestedTabularInline

from .forms import ChecklistTypeForm
from .models import Checklist, ChecklistQuestion, ChecklistType, QuestionChoice


class QuestionChoiceAdmin(NestedTabularInline):
    list_display = ("question", "name", "value")
    date_hierarchy = "created"
    autocomplete_fields = ("question",)
    model = QuestionChoice
    extra = 0


class ChecklistQuestionAdmin(NestedStackedInline):
    list_display = ("checklist_type", "question")
    list_filter = ("checklist_type",)
    search_fields = ("question",)
    date_hierarchy = "created"
    autocomplete_fields = ("checklist_type",)
    inlines = [QuestionChoiceAdmin]
    model = ChecklistQuestion
    extra = 0
    ordering = ["order"]


class ChecklistTypeAdmin(NestedModelAdmin):
    list_display = ("zaaktype_omschrijving", "zaaktype_catalogus")
    list_filter = ("zaaktype_omschrijving",)
    search_fields = ("zaaktype_omschrijving",)
    date_hierarchy = "created"
    form = ChecklistTypeForm
    inlines = [ChecklistQuestionAdmin]
    extra = 0


admin.site.register(ChecklistType, ChecklistTypeAdmin)


@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = (
        "zaak",
        "checklist_type",
    )
    list_filter = ("checklist_type",)
    date_hierarchy = "created"
