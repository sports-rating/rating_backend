from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error

from apps.education.models import (
    Education,
    School
)

from apps.sport.models import (
    Sport
)

from apps.sport.serializers import (
    SportSerializer,
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


class SchoolSerializer(serializers.ModelSerializer):
    sport_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=True)
    sports = SportSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = School
        fields = [
            "id",
            "name",
            "phone_number",
            "director",
            "type",
            "address",
            "sport_ids",
            "sports"
        ]
        extra_kwargs = {"id": {"read_only": True},}

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")

        if School.objects.filter(phone_number=phone_number).exists():
            raise_validation_error(message=_("Phone number is already registered"))

        return attrs

    def create(self, validated_data):
        sport_ids = validated_data.pop("sport_ids", None)

        with transaction.atomic():
            school = School.objects.create(**validated_data)

            if sport_ids:
                sport_objects = Sport.objects.filter(id__in=sport_ids)
                if not sport_objects.exists():
                    raise_validation_error(message=_(f"At least one sport must be included"))
                school.sports.set(sport_objects)

        return school

    def update(self, instance, validated_data):
        sport_ids = validated_data.pop("sport_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if sport_ids:
            sport_objects = Sport.objects.filter(id__in=sport_ids)
            if not sport_objects.exists():
                raise_validation_error(message=_("At least one sport must be included"))
            instance.sports.set(sport_objects)

        return instance
