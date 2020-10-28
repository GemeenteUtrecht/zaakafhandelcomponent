from django.db.models import Q
from django.forms.fields import CharField, MultipleChoiceField

from django_filters import rest_framework as filters
from rest_framework import viewsets

from zac.utils import pagination

from ..models import User
from .serializers import UserSerializer


class MultipleValueField(MultipleChoiceField):
    def __init__(self, *args, field_class, **kwargs):
        self.inner_field = field_class()
        super().__init__(*args, **kwargs)

    def valid_value(self, value):
        return self.inner_field.validate(value)

    def clean(self, values):
        return values and [self.inner_field.clean(value) for value in values]


class MultipleValueFilter(filters.Filter):
    field_class = MultipleValueField

    def __init__(self, *args, field_class, **kwargs):
        kwargs.setdefault("lookup_expr", "in")
        super().__init__(*args, field_class=field_class, **kwargs)


class UserFilter(filters.FilterSet):
    search = filters.CharFilter(method="search_multiple_fields")
    exclude = MultipleValueFilter(
        field_name="username", field_class=CharField, exclude=True
    )
    include = MultipleValueFilter(field_name="username", field_class=CharField)

    class Meta:
        model = User
        fields = ["search", "exclude", "include"]

    def search_multiple_fields(self, qs, name, value):
        return qs.filter(
            Q(username__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
        )


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = pagination.PageNumberPagination
    page_size = 100
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = UserFilter
