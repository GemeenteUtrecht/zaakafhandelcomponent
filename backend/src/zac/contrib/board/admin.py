from django.contrib import admin

from .models import Board, BoardColumn, BoardItem


class BoardColumnInline(admin.TabularInline):
    model = BoardColumn
    prepopulated_fields = {"slug": ("name",)}
    extra = 0


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created", "modified")
    search_fields = ("uuid",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [BoardColumnInline]


@admin.register(BoardColumn)
class BoardColumnAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "board", "created", "modified")
    list_filter = ("board__slug",)
    search_fields = ("uuid", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BoardItem)
class BoardItemAdmin(admin.ModelAdmin):
    list_display = ("object_type", "object", "column")
    list_filter = ("object_type", "column__board__slug")
    search_fields = ("uuid", "object")
