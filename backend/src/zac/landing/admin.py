from django.utils.translation import gettext as _
from solo.admin import SingletonModelAdmin
from django.contrib import admin
import nested_admin

from .models import LandingPageConfiguration, LandingPageSection, LandingPageLink


class BaseLandingPageLinkInline(nested_admin.NestedStackedInline):
    model = LandingPageLink
    # sortable_field_name = "label"


class LandingPageSectionLinkInline(BaseLandingPageLinkInline):
    extra = 0
    fields = ("icon", "label", "href",)
    verbose_name_plural = _("Sectie links")


class LandingPageFooterLinkInline(BaseLandingPageLinkInline):
    fields = ("label", "href",)
    verbose_name_plural = _("Footer links")


class LandingPageSectionInline(nested_admin.NestedStackedInline):
    extra = 1
    model = LandingPageSection
    # sortable_field_name = "name"
    inlines = [LandingPageSectionLinkInline]


@admin.register(LandingPageConfiguration)
class LandingPageConfigurationAdmin(nested_admin.NestedModelAdmin, SingletonModelAdmin):
    inlines = [LandingPageSectionInline, LandingPageFooterLinkInline]
