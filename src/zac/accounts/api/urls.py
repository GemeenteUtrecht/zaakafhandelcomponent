from django.urls import path

from zac.accounts.api.views import InformatieobjecttypenJSONView

app_name = "accounts"

urlpatterns = [
    path(
        "informatieobjecttypen",
        InformatieobjecttypenJSONView.as_view(),
        name="informatieobjecttypen",
    ),
]
