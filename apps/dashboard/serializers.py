from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from user.models import (
    Sportsman,
    Media,
    Education,
    Result
)

from user.serializers import (
    UsersMeSerializer
)

from shared.addons.exceptions import raise_validation_error
from shared.addons.utils import CorrectPath


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            "name",
            "sport_type",
            "start_year",
            "end_year",
            "currently_studying",
        ]

    def validate(self, attrs):
        start_year = attrs.get("start_year")
        end_year = attrs.get("end_year")
        if start_year and end_year and start_year >= end_year:
            raise_validation_error(message=_("Start year must be less than end year"))
        return attrs


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = [
            "tournament_name",
            "country",
            "start_year",
            "end_year",
            "currently_participating",
            "rating",
            "logo",
        ]

    def validate(self, attrs):
        start_year = attrs.get("start_year")
        end_year = attrs.get("end_year")
        if start_year and end_year and start_year >= end_year:
            raise_validation_error(message=_("Start year must be less than end year"))
        return attrs


class MediaSerializer(serializers.ModelSerializer):
    owner = serializers.ChoiceField(
        choices=(("sportsman", "sportsman"), ("trainer", "trainer"), ("media", "media")), write_only=True
    )

    class Meta:
        model = Media
        fields = [
            "id", "media_type", "size", "extension", "created_time", "file", "owner"
        ]
        read_only_fields = ["created_time", "size", "extension", "media_type"]

    def create(self, validated_data):
        owner = validated_data.pop("owner", None)
        media_instance = Media(**validated_data)

        if owner:
            correct_path = CorrectPath('media', owner=owner)
            media_instance.file.field.upload_to = correct_path
        media_instance.save()
        return media_instance


class SportsmanRegisterSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True, required=True)
    results = ResultSerializer(many=True, required=True)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=True)

    class Meta:
        model = Sportsman
        fields = [
            "sport_type",
            "sport_direction",
            "motto",
            "height",
            "weight",
            "gender",
            "region",
            "city",
            "street",
            "place_of_birth",
            "citizenship",
            "telegram",
            "instagram",
            "educations",
            "media_ids",
            "results",
        ]
    
    def create(self, validated_data):
        educations_data = validated_data.pop("educations")
        results_data = validated_data.pop("results")
        media_ids = validated_data.pop("media_ids")

        profile = Sportsman.objects.create(**validated_data)

        # Link existing media to the sportsman profile
        media_objects = Media.objects.filter(id__in=media_ids)
        profile.media.set(media_objects)

        for education_data in educations_data:
            Education.objects.create(sportsman_profile=profile, **education_data)
        
        for result_data in results_data:
            Result.objects.create(sportsman_profile=profile, **result_data)
        
        return profile


class SportsmanSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True)
    results = ResultSerializer(many=True)
    media = MediaSerializer(many=True)
    user = UsersMeSerializer()

    class Meta:
        model = Sportsman
        fields = [
            "user",
            "sport_type",
            "sport_direction",
            "motto",
            "height",
            "weight",
            "gender",
            "region",
            "city",
            "street",
            "place_of_birth",
            "citizenship",
            "telegram",
            "instagram",
            "educations",
            "media",
            "results",
        ]
