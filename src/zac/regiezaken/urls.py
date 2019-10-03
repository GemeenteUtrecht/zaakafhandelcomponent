from django.urls import path

from .views import IndexView, LoginView, RegieZaakDetailView, ZaakDetailView

app_name = 'regiezaken'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path("login/", LoginView.as_view(), name="login"),
    path("<pk>/", RegieZaakDetailView.as_view(), name="regiezaak-detail"),
    path('<pk>/zaken/<uuid>/', ZaakDetailView.as_view(), name='zaak-detail'),
]
