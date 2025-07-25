from datetime import datetime

from django.utils.translation import gettext as _
from django.db import transaction

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from user.models import (
    User,
    Sportsman,
    Trainer,
)

from .models import PrivacyPolicy, TermsOfCondition

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.utils import CorrectPath


# class InlineMediaSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Media
#         fields = [
#             "id",
#             "media_type",
#             "file",
#             "size",
#             "extension",
#         ]


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "email",
            "user_role",
            "created_time",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.user_role == "sportsman":
            if instance.sportsman_profile:
                data["sport"] = instance.sportsman_profile.sport.name if instance.sportsman_profile.sport else None
                if instance.sportsman_profile.trainer:
                    data["trainer_id"] = instance.sportsman_profile.trainer.user_id
                    data["trainer_name"] = f'{instance.sportsman_profile.trainer.user}'
        if instance.user_role == "trainer":
            if instance.trainer_profile:
                data["sport"] = instance.trainer_profile.sport.name if instance.trainer_profile.sport else None
        return data


class SportsmanExportSerializer(serializers.ModelSerializer):
    height = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    street = serializers.SerializerMethodField()
    citizenship = serializers.SerializerMethodField()

    class Meta:
        model = Sportsman
        fields = [
            "height",
            "weight",
            "region",
            "city",
            "street",
            "citizenship",
        ]

    def get_height(self, obj):
        return obj.user_metrics.get("height") if obj.user_metrics else None
    
    def get_weight(self, obj):
        return obj.user_metrics.get("weight") if obj.user_metrics else None

    def get_region(self, obj):
        return obj.address.get("region") if obj.address else None

    def get_city(self, obj):
        return obj.address.get("city") if obj.address else None

    def get_street(self, obj):
        return obj.address.get("street") if obj.address else None

    def get_citizenship(self, obj):
        return obj.address.get("citizenship") if obj.address else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.trainer:
            data["trainer_name"] = f'{instance.trainer.user}'
        if instance.sport:
            data["sport"] = instance.sport.name
        return data


class TrainerExportSerializer(serializers.ModelSerializer):
    height = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    street = serializers.SerializerMethodField()
    citizenship = serializers.SerializerMethodField()

    class Meta:
        model = Sportsman
        fields = [
            "height",
            "weight",
            "region",
            "city",
            "street",
            "citizenship",
        ]

    def get_height(self, obj):
        return obj.user_metrics.get("height") if obj.user_metrics else None
    
    def get_weight(self, obj):
        return obj.user_metrics.get("weight") if obj.user_metrics else None

    def get_region(self, obj):
        return obj.address.get("region") if obj.address else None

    def get_city(self, obj):
        return obj.address.get("city") if obj.address else None

    def get_street(self, obj):
        return obj.address.get("street") if obj.address else None

    def get_citizenship(self, obj):
        return obj.address.get("citizenship") if obj.address else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.sport:
            data["sport"] = instance.sport.name
        return data


class UserExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "email",
            "user_role",
            "birth_date",
            "created_time",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        if instance.user_role == "sportsman":
            sportsman_data = SportsmanExportSerializer(instance.sportsman_profile).data
            data.update(sportsman_data)  # Merge sportsman data into the main data

        elif instance.user_role == "trainer":
            trainer_data = TrainerExportSerializer(instance.trainer_profile).data
            data.update(trainer_data)  # Merge trainer data into the main data

        return data
    

class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = ("id", "title", "language", "text")

    def validate(self, attrs):
        language = attrs.get('language')
        instance = self.instance

        if instance:
            current_language = instance.language
            is_language_updated = language is not None and language != current_language

            if is_language_updated:                
                queryset = PrivacyPolicy.objects.filter(language=language)
                queryset = queryset.exclude(id=instance.id)

                if queryset.exists():
                    raise_validation_error(_("Privacy Policy with this language already exists"))
        else:
            if language:
                if PrivacyPolicy.objects.filter(language=language).exists():
                    raise_validation_error(message=_("Privacy Policy with this language already exists"))

        return attrs


class TermsOfConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsOfCondition
        fields = ("id", "title", "language", "text")

    def validate(self, attrs):
        language = attrs.get("language")
        instance = self.instance

        if instance:
            current_language = instance.language
            is_language_updated = language is not None and language != current_language

            if is_language_updated:
                queryset = TermsOfCondition.objects.filter(language=language)
                queryset.exclude(id=instance.id)

                if queryset.exists():
                    raise_validation_error(_("Terms of Conditions with language already exists"))
        else:
            if language:
                if TermsOfCondition.objects.filter(language=language).exists():
                    raise_validation_error(message=_("Terms of Conditions with this language already exists"))
            
        return attrs