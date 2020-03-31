from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import redirect
from django.views import View


class FlushCacheView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        referer = request.META["HTTP_REFERER"]
        cache.clear()
        return redirect(referer)
