from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.db.models import Sum, QuerySet
from django.conf import settings

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.general import (
    check_uniqueness,
    check_m2m_uniqueness
)

from apps.career.models import (
    Education
)

from apps.sport.models import (
    Sport,
    School
)


class EducationCreateSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True) # sport
    school_id = serializers.PrimaryKeyRelatedField(queryset=School.objects.all(), source="school", write_only=True)

    class Meta:
        model = Education
        fields = [
            "id",
            "sport_id",
            "school_id",
            "start_year",
            "end_year",
            "currently_studying",
        ]
        extra_kwargs = {"id": {"read_only": True},}

    def validate(self, attrs):
        start_year = attrs.get("start_year")
        end_year = attrs.get("end_year")
        if start_year and end_year and start_year >= end_year:
            raise_validation_error(message=_("Start year must be less than end year"))

        return attrs

    def create(self, validated_data):
        sport = validated_data.pop("sport")
        school = validated_data.pop("school")
        education = Education.objects.create(sport=sport, school=school, **validated_data)
        return education

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport"] = instance.sport.name
        if instance.school:
            data["school_id"] = instance.school.id
            data["school_name"] = instance.school.name
        return data


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = (
            "id",
            "start_year",
            "end_year",
            "school",
            "currently_studying",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.sport:
            data["sport_id"] = instance.sport.id
            data["sport"] = instance.sport.name
        if instance.school:
            data["school_id"] = instance.school.id
            data["school_name"] = instance.school.name
        return data
