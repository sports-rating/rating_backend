from datetime import datetime
from typing import Optional

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
from apps.shared.utils.general import (
    get_file_full_url,
    calculate_file_size,
    check_uniqueness,
    request_type_theme_mapping
)

from apps.federation.models import (
    Federation,
    AgeGroup,
    FederationAgeGroup,
    FederationDocument
)

from apps.user.models import (
    User,
    Trainer,
    ArchivedTrainer,
    UserRequest
)

from apps.dashboard.serializers import (
    UserListSerializer
)

from apps.sport.serializers import SportSerializer


class AgeGroupSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = AgeGroup
        fields = (
            "id",
            "name",
            "sport",
            "age",
            "weights",
            "gender",
            "created_time"
        )
        validators = []


class FederationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FederationDocument
        fields = [
            "id",
            "file",
            "media_type",
            "size"
        ]
        read_only_fields = ("id", "media_type", "size")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['file'] = get_file_full_url(instance.file.url) if instance.file else None
        data["size"] = calculate_file_size(instance.size) if instance.size else None
        return data


class FederationSerializer(serializers.ModelSerializer):
    documents = FederationDocumentSerializer(many=True, required=False)
    age_groups = AgeGroupSerializer(many=True, required=False)

    class Meta:
        model = Federation
        fields = (
            "id",
            "name",
            "is_national",
            "users",
            "parent_federation",
            "region",
            "sports",
            "address",
            "phone_number",
            "email",
            "logo",
            "documents",
            "age_groups",
            "social_media",
            "created_time",
        )
        read_only_fields = ("id", "created_time")
        extra_kwargs = {
            "logo": {"required": False},
            "parent_federation": {"required": False},
            "region": {"required": False},
            "users": {"required": False}
        }

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        documents = attrs.get('documents', [])
        is_national = attrs.get("is_national", False)
        region = attrs.get("region", None)

        check_uniqueness("name", attrs, Federation, instance)
        check_uniqueness("phone_number", attrs, Federation, instance)

        if is_national and region:
            raise_validation_error(message=_("National federations cannot have a region."))
        if not isinstance(documents, list):
            raise_validation_error(message=_("Documents must be a list of files."))
        return attrs

    def create(self, validated_data):
        age_groups_data = validated_data.pop("age_groups", [])
        user = self.context.get("request").user
        users = validated_data.pop("users", [])

        sports = validated_data.pop("sports", [])
        documents = validated_data.pop("documents", [])
        with transaction.atomic():
            federation = Federation.objects.create(**validated_data)
            for doc in documents:
                FederationDocument.objects.create(federation=federation, **doc).save()
            federation.users.set([user])
            federation.sports.set(sports)
            for age_group_data in age_groups_data:
                age_group = AgeGroup.objects.create(**age_group_data)
                FederationAgeGroup.objects.create(federation=federation, age_group=age_group)
        return federation

    def update(self, instance, validated_data):
        age_groups = validated_data.pop("age_groups", [])
        users = validated_data.pop("users", [])
        sports = validated_data.pop("sports", [])
        documents = validated_data.pop("documents", [])

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if users:
                instance.users.set(users)

            if sports:
                instance.sports.set(sports)

            if documents:
                instance.documents.all().delete()
                for doc in documents:
                    FederationDocument.objects.create(federation=instance, **doc).save()

            # CUD(Create, Update, Delete) pattern is being used here
            if age_groups:
                left_age_groups_id = []

                for age_group in age_groups:
                    age_group_id = age_group.get("id", None)
                    if age_group_id:  # if id exists, update the existing age group
                        AgeGroup.objects.filter(id=age_group_id).update(**age_group)
                        left_age_groups_id.append(age_group_id)
                    else:  # if id does not exist, create a new age group
                        new_age_group = AgeGroup.objects.create(**age_group)
                        FederationAgeGroup.objects.create(federation=instance, age_group=new_age_group)
                        left_age_groups_id.append(new_age_group.id)

                # Delete age groups that are no longer present
                FederationAgeGroup.objects.filter(federation=instance).exclude(age_group__id__in=left_age_groups_id).delete()
                AgeGroup.objects.exclude(id__in=left_age_groups_id).delete()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['logo'] = get_file_full_url(instance.logo.url) if instance.logo else None
        data['age_groups'] = AgeGroupSerializer(
            [fa.age_group for fa in instance.age_group_links.all()],
            many=True,
        ).data
        data['documents'] = FederationDocumentSerializer(
            instance.documents.all(),
            many=True
        ).data
        data['region'] = {
            "id": instance.region.id,
            "name": instance.region.name
        } if instance.region else None
        data['users'] = UserListSerializer(
            instance.users.all(),
            many=True
        ).data
        data['sports'] = SportSerializer(
            instance.sports.all(),
            many=True,
        ).data
        return data


class FederationUserRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRequest
        fields = [
            "id",
            "sender",
            "receivers",
            "request_type",
            "status",
            "created_time",
        ]
        read_only_fields = ["id", "sender", "created_time"]
        extra_kwargs = {
            "status": {"required": False}
        }

    def _get_sender_sport(self, instance):
        if instance.sender.user_role == "sportsman":
            return instance.sender.sportsman_profile.sport
        elif instance.sender.user_role == "trainer":
            return instance.sender.trainer_profile.sport
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        receiver = self.context.get("request").user
        federation_id = self.context.get("federation_id")
        sport = self._get_sender_sport(instance)
        data["sender"] = {
            "id": instance.sender.id,
            "full_name": instance.sender.full_name,
            "user_role": instance.sender.user_role,
            "phone_number": instance.sender.phone_number,
        }
        logger.info(f"Receivers: {instance.receivers}")
        federation = Federation.objects.filter(id=federation_id).first()
        data["receiver"] = {
            "id": receiver.id,
            "full_name": receiver.full_name,
            "user_role": receiver.user_role,
            "phone_number": receiver.phone_number,
            "federation": {
                "id": federation.id,
                "name": federation.name
            } if federation else None
        }
        data["request_theme"] = request_type_theme_mapping(instance.request_type)
        data["sport"] = {
            "id": sport.id,
            "name": sport.name,
            "logo": get_file_full_url(sport.logo.url) if sport.logo else None
        } if sport else None
        data.pop("receivers", None)
        return data
