from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.settings import api_settings


class IgnoreCamelCaseJSONParser(CamelCaseJSONParser):
    json_underscoreize = {
        **api_settings.JSON_UNDERSCOREIZE,
        "ignore_fields": ("eigenschappen",),
    }
