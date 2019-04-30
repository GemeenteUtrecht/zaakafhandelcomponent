from django.views import View
from django.views.generic.base import ContextMixin, TemplateResponseMixin


class BaseListView(TemplateResponseMixin, ContextMixin, View):
    context_object_name = None
    filter_form_class = None

    def get_object_list(self):
        raise NotImplementedError

    def get_filter_form_initial(self):
        return None

    def get_filter_form(self):
        if self.filter_form_class is None:
            return

        if not hasattr(self, '_filter_form'):
            data = self.request.GET or None
            self._filter_form = self.filter_form_class(
                data=data,
                initial=self.get_filter_form_initial()
            )

        return self._filter_form

    def get_context_data(self, **kwargs):
        context = {
            self.context_object_name: self.object_list,
            'object_list': self.object_list,
            'filter_form': self.get_filter_form(),
        }
        context.update(kwargs)
        return super().get_context_data(**context)

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_object_list()
        context = self.get_context_data()
        return self.render_to_response(context)


class BaseDetailView(TemplateResponseMixin, ContextMixin, View):
    """
    A base view to look up remote objects.

    TODO: support caching
    """

    def get_object(self):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = {
            self.context_object_name: self.object,
            'object': self.object,
        }
        context.update(kwargs)
        return super().get_context_data(**context)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        return self.render_to_response(context)
