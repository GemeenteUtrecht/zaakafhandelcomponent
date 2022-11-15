from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import LandingPageConfigurationView

router = DefaultRouter(trailing_slash=False)

urlpatterns = router.urls
urlpatterns = [
    path(
        "",
        LandingPageConfigurationView.as_view(),
        name="landing-page-configuration",
    ),
]
