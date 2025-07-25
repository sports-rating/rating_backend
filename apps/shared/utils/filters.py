from django.db import models
from django_filters import rest_framework as filters


class BaseFilterSet(filters.FilterSet):
    start_created_time = filters.DateTimeFilter(field_name="created_time", lookup_expr="gte")
    end_created_time = filters.DateTimeFilter(field_name="created_time", lookup_expr="lte")
    start_updated_time = filters.DateTimeFilter(field_name="updated_time", lookup_expr="gte")
    end_updated_time = filters.DateTimeFilter(field_name="updated_time", lookup_expr="lte")

    def filter_queryset(self, queryset):
        for name, value in self.form.cleaned_data.items():
            if not value:
                continue
            queryset = self.filters[name].filter(queryset, value)
            assert isinstance(
                queryset, models.QuerySet
            ), "Expected '%s.%s' to return a QuerySet, but got a %s instead." % (
                type(self).__name__,
                name,
                type(queryset).__name__,
            )
        return queryset
