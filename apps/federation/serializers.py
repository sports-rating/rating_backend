import typing as t
import re

from uuid import UUID
from datetime import datetime

from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.db.models import Sum, QuerySet
from django.conf import settings

from rest_framework import serializers

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.general import (
    get_file_full_url,
    calculate_file_size,
    check_uniqueness,
    check_m2m_uniqueness,
    request_type_theme_mapping
)
from apps.shared.utils.mixins import RequestContextMixin
from apps.shared.utils.types import *

from apps.federation.models import (
    Federation,
    AgeGroup,
    FederationAgeGroup,
    FederationDocument
)
from apps.sport.models import (
    Sport
)
from apps.user.models import (
    User,
    UserRequest
)

from apps.dashboard.serializers import (
    UserListSerializer
)
from apps.sport.serializers import SportSerializer
from apps.shared.utils import enums


class AgeGroupSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    PATTERN_1 = "U-17"
    PATTERN_2 = "+45"
    PATTERN_3 = "U-18-35"

    class Meta:
        model = AgeGroup
        fields = (
            "id",
            "name",
            "sport",
            "sport_type",
            "min_age",
            "max_age",
            "weights",
            "gender",
            "created_time"
        )

    def validate(self, attrs):
        """
        Parse `name` into min_age and max_age:
        - U-17
        - +45
        - U-17-45
        """
        name = attrs.get("name", "")

        # Match patterns like U-17, U-17-45, +45
        u_match = re.match(r'^U-(\d+)(?:-(\d+))?$', name)
        plus_match = re.match(r'^\+(\d+)$', name)

        # logger.info(f"U-match: {u_match}, Plus-match: {plus_match}")

        if u_match:
            attrs["max_age"] = int(u_match.group(1))
            if u_match.group(2):
                attrs["min_age"] = int(u_match.group(1))
                attrs["max_age"] = int(u_match.group(2))
            else:
                attrs["min_age"] = None

        elif plus_match:
            attrs["min_age"] = int(plus_match.group(1))
            attrs["max_age"] = None

        else:
            raise_validation_error(message=_(f"Invalid age group name format. Use {self.PATTERN_1}, {self.PATTERN_3}, or {self.PATTERN_2}."))
        return attrs

    def to_representation(self, instance: AgeGroup) -> dict:
        data = super().to_representation(instance)
        data["sport"] = {
            "id": instance.sport.id,
            "name": instance.sport.name,
            "logo": get_file_full_url(instance.sport.logo.url) if instance.sport.logo else None
        } if instance.sport else None
        data["sport_type"] = {
            "id": instance.sport_type.id,
            "name": instance.sport_type.name
        } if instance.sport_type else None
        return data


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

    def to_representation(self, instance: FederationDocument) -> dict:
        data = super().to_representation(instance)
        data['file'] = get_file_full_url(instance.file.url) if instance.file else None
        data["size"] = calculate_file_size(instance.size) if instance.size else None
        return data


class FederationSerializer(RequestContextMixin, serializers.ModelSerializer):
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

    def validate(self, attrs: dict) -> dict:
        instance = getattr(self, 'instance', None)
        documents = attrs.get('documents', [])
        is_national = attrs.get("is_national", False)
        region = attrs.get("region", None)
        sports: list[Sport] = attrs.get("sports", [])
        logger.info(f"Sports type: {type(sports)}")
        logger.info(f"Sports: {sports}")
        check_uniqueness("name", attrs, Federation, instance)
        check_uniqueness("phone_number", attrs, Federation, instance)
        check_m2m_uniqueness("sports", attrs, Federation, instance)

        if is_national and region:
            raise_validation_error(message=_("National federations cannot have a region."))
        if not isinstance(documents, list):
            raise_validation_error(message=_("Documents must be a list of files."))
        return attrs

    def create(self, validated_data: dict) -> Federation:
        age_groups_data = validated_data.pop("age_groups", [])
        admin_users: QuerySet[User] = User.objects.filter(user_role__in=[enums.UserRoles.ADMIN.value])
        sports = validated_data.pop("sports", [])
        documents = validated_data.pop("documents", [])
        validated_data.pop("users", None)  # we will set users after creation

        with transaction.atomic():
            federation: Federation = Federation.objects.create(**validated_data)
            for doc in documents:
                FederationDocument.objects.create(federation=federation, **doc).save()
            federation.users.set(admin_users)
            federation.sports.set(sports)
            for age_group_data in age_groups_data:
                age_group = AgeGroup.objects.create(**age_group_data)
                FederationAgeGroup.objects.create(federation=federation, age_group=age_group)
        return federation

    def update(self, instance: Federation, validated_data: dict) -> Federation:
        age_groups = validated_data.pop("age_groups", [])
        users: list[User] = validated_data.pop("users", [])
        sports: list[Sport] = validated_data.pop("sports", [])
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
                left_age_groups_id: list = []

                for age_group in age_groups:
                    age_group_id: UUID = age_group.get("id", None)
                    if age_group_id:  # if id exists, update the existing age group
                        AgeGroup.objects.filter(id=age_group_id).update(**age_group)
                        left_age_groups_id.append(age_group_id)
                    else:  # if id does not exist, create a new age group
                        new_age_group: AgeGroup = AgeGroup.objects.create(**age_group)
                        FederationAgeGroup.objects.create(federation=instance, age_group=new_age_group)
                        left_age_groups_id.append(new_age_group.id)

                # Delete age groups that are no longer present
                FederationAgeGroup.objects.filter(federation=instance).exclude(age_group__id__in=left_age_groups_id).delete()
                # Delete orphan AgeGroups (those that no longer belong to any federation)
                AgeGroup.objects.filter(
                    federation_links__isnull=True  # no federation links
                ).delete()
        return instance

    def to_representation(self, instance: Federation) -> dict:
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


class FederationUserRequestSerializer(RequestContextMixin, serializers.ModelSerializer):
    class Meta:
        model = UserRequest
        fields = [
            "id",
            "sender",
            "receivers",
            "request_type",
            "status",
            "message_from_sender",
            "message_from_receiver",
            "old_data",
            "new_data",
            "processed_by",
            "processed_time",
            "created_time",
        ]
        read_only_fields = ["id", "sender", "created_time"]
        extra_kwargs = {
            "status": {"required": False}
        }

    def _get_sender_sport(self, instance: UserRequest) -> t.Union[Sport, None]:
        if instance.sender.user_role == "sportsman":
            return instance.sender.sportsman_profile.sport
        elif instance.sender.user_role == "trainer":
            return instance.sender.trainer_profile.sport
        return None

    def to_representation(self, instance: UserRequest) -> dict:
        data = super().to_representation(instance)
        receiver: User = self.request.user  # type: ignore

        # NOTE: CoderB7 -> cast tells mypy: trust me, this is a UUID.
        # It does not change runtime behavior
        federation_id: UUID = t.cast(UUID, self.context.get("federation_id"))
        sport: Sport | None = self._get_sender_sport(instance)
        data["sender"] = {
            "id": instance.sender.id,
            "full_name": instance.sender.full_name,
            "user_role": instance.sender.user_role,
            "phone_number": instance.sender.phone_number,
        }
        federation: Federation | None = Federation.objects.filter(id=federation_id).first()
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
        data["processed_by"] = {
            "id": instance.processed_by.id,
            "full_name": instance.processed_by.full_name,
            "phone_number": instance.processed_by.phone_number,
        } if instance.processed_by else None
        data["processed_time"] = datetime.strftime(instance.processed_time, "%Y-%m-%d %H:%M:%S") if instance.processed_time else None
        data.pop("receivers", None)
        return data


class FederationUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "email",
            "birth_date",
            "region",
            "district",
            "gender",
            "user_role",
            "created_time"
        ]
        read_only_fields = ["id", "created_time"]

    def to_representation(self, instance: User) -> dict:
        data = super().to_representation(instance)
        sport: Sport | None = self._get_sport(instance)
        trainer: User | None = self._get_trainer(instance)
        data["full_name"] = instance.full_name
        data["region"] = {
            "id": instance.region.id,
            "name": instance.region.name
        } if instance.region else None
        data["district"] = {
            "id": instance.district.id,
            "name": instance.district.name
        } if instance.district else None
        data["sport"] = {
            "id": sport.id,
            "name": sport.name,
            "logo": get_file_full_url(sport.logo.url) if sport.logo else None
        } if sport else None
        if instance.user_role == enums.UserRoles.SPORTSMAN.value:
            data["trainer"] = {
                "id": trainer.id,
                "full_name": trainer.full_name,
                "user_role": trainer.user_role,
                "phone_number": trainer.phone_number,
            } if trainer else None
            data["is_result_paid"] = instance.sportsman_profile.is_result_paid
        elif instance.user_role == enums.UserRoles.TRAINER.value:
            data["federation"] = {
                "id": instance.trainer_profile.federation.id,
                "name": instance.trainer_profile.federation.name
            }
        return data

    def _get_sport(self, instance: User) -> t.Union[Sport, None]:
        if instance.user_role == "sportsman":
            return instance.sportsman_profile.sport
        elif instance.user_role == "trainer":
            return instance.trainer_profile.sport
        return None

    def _get_trainer(self, instance: User) -> t.Union[User, None]:
        if instance.user_role == "sportsman":
            return instance.sportsman_profile.trainer.user
        return None


class FederationAgeGroupSerializer(RequestContextMixin, serializers.ModelSerializer):
    age_group = AgeGroupSerializer(read_only=True)

    class Meta:
        model = FederationAgeGroup
        fields = [
            "id",
            "age_group",
            "is_active",
            "created_time"
        ]
        read_only_fields = ["id", "created_time"]
