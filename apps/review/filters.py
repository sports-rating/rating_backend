from django_filters import rest_framework as filters
from django.db.models import F, Q

from apps.shared.utils.filters import BaseFilterSet
from apps.review.models import (
    Comment
)


class CommentFilter(BaseFilterSet):
    sport_institution = filters.CharFilter(field_name="sport_institution__id")
    rating = filters.NumberFilter(field_name="rating")

    class Meta:
        model = Comment
        fields = ["sport_institution", "rating"]
