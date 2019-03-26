from django.views.generic import TemplateView

from .services import get_zaaktypes, get_zaken


class Index(TemplateView):
    """
    Display the landing screen.
    """
    template_name = 'core/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zaaktypes'] = get_zaaktypes()
        context['zaken'] = get_zaken()
        return context
