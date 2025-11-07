from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import ContextMixin, TemplateResponseMixin


class BaseListView(TemplateResponseMixin, ContextMixin, View):
    context_object_name = None
    filter_form_class = None

    def get_object_list(self):
        raise NotImplementedError

    def get_filter_form_initial(self):
        return None

    def get_filter_form_kwargs(self) -> dict:
        data = self.request.GET or None
        initial = self.get_filter_form_initial()
        return {
            "data": data,
            "initial": initial,
        }

    def get_filter_form(self):
        if self.filter_form_class is None:
            return

        if not hasattr(self, "_filter_form"):
            form_kwargs = self.get_filter_form_kwargs()
            self._filter_form = self.filter_form_class(**form_kwargs)

        return self._filter_form

    def get_context_data(self, **kwargs):
        context = {
            self.context_object_name: self.object_list,
            "object_list": self.object_list,
            "filter_form": self.get_filter_form(),
        }
        context.update(kwargs)
        return super().get_context_data(**context)

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_object_list()
        context = self.get_context_data()
        return self.render_to_response(context)


class SingleObjectMixin(ContextMixin):
    context_object_name = "object"

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except ObjectDoesNotExist:
            raise Http404(
                _("No %(verbose_name)s found matching the query")
                % {"verbose_name": self.context_object_name}
            )

    def get_object(self):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = {self.context_object_name: self.object, "object": self.object}
        context.update(kwargs)
        return super().get_context_data(**context)


class BaseDetailView(TemplateResponseMixin, SingleObjectMixin, View):
    """
    A base view to look up remote objects.
    """

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        return self.render_to_response(context)
