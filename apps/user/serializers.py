from decimal import Decimal, InvalidOperation
import typing as t

from datetime import date
from typing import Any, Dict, List

import rest_framework_simplejwt.serializers as jwt_serializers
import rest_framework_simplejwt.tokens as jwt_tokens
from rest_framework.generics import get_object_or_404
from rest_framework import serializers

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.db import IntegrityError, transaction
from django.db.models import Sum, QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _


from fcm_django.models import DeviceType, FCMDevice

from apps.career.models import Education
from apps.shared.models import District, Neighborhood, Region
from apps.shared.utils import enums
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.general import get_file_full_url
# custom
from apps.shared.utils.logging import logger
from apps.shared.utils.notifications import send_notification_to_user
from apps.shared.utils.utils import CorrectPath
from apps.sport.models import Sport, Tournament
from apps.career.models import Result
from apps.federation.models import Federation
from apps.career.serializers import ResultCreateSerializer, EducationSerializer
from apps.user.models import (
    ArchivedTrainer, Sportsman, Trainer, User,
    UserMedia, UserNotification, UserRequest
)
from apps.user.utils import (
    calculate_sportsman_statistics,
    calculate_trainer_statistics
)
from apps.shared.services.user_request import UserRequestService
from apps.shared.services.snapshot_service import SnapshotService
from apps.shared.services.scoring_service import ScoringService
from apps.shared.utils.mixins import RequestContextMixin
from apps.shared.utils.payloads import (
    SPORTSMAN_APPROVAL_REQUIRED_FIELDS,
    TRAINER_APPROVAL_REQUIRED_FIELDS,
    SPORTSMAN_RESULT_APPROVAL_REQUIRED_FIELDS
)
from apps.shared.serializers import (
    SportsmanResultSnapshotSerializer
)


SEND_VERIFICATION_ACTION = (
    ("signup", "signup"),
    ("login", "login"),
    ("forgot_password", "forgot_password"),
    ("change_phone_number", "change_phone_number"),
)


class SendVerificationCodeSerializer(serializers.Serializer): # noqa
    phone_number = serializers.CharField()
    action = serializers.ChoiceField(choices=SEND_VERIFICATION_ACTION)

    def validate(self, attrs):
        action = attrs.get("action")
        phone_number = attrs.get("phone_number")
        user = User.objects.filter(phone_number=phone_number).first()

        if action == "signup" and user:
            raise_validation_error(message=_("Phone number is already registered"))

        if action in ["forgot_password", "login"] and not user:
            raise_validation_error(message=_("Your phone number is not registered"))

        return attrs


class VerifyCodeSerializer(serializers.Serializer):  # noqa
    code = serializers.CharField()
    phone_number = serializers.CharField()
    action = serializers.ChoiceField(choices=SEND_VERIFICATION_ACTION, required=False)
    fcm_token = serializers.CharField(required=False)
    device_type = serializers.ChoiceField(choices=DeviceType.choices, required=False)

    def get_tokens(self):  # noqa
        action = self.validated_data.get("action", None)
        phone_number = self.validated_data.get("phone_number")
        fcm_token = self.validated_data.get('fcm_token')
        device_type = self.validated_data.get('device_type')

        if action == "login":
            user = User.objects.filter(phone_number=phone_number).first()
            if not user:
                raise_validation_error(message=_("User not found"))
            if fcm_token:
                FCMDevice.objects.update_or_create(
                    registration_id=fcm_token,
                    defaults={
                        'user': user,
                        'type': device_type,
                        'active': True,
                    }
                )
            return {
                'tokens': user.tokens(),
                'user_role': user.user_role
            }
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.validated_data.get('action') == 'login':
            user_data = self.get_tokens()
            data["tokens"] = user_data.get('tokens')
            data["user_role"] = user_data.get('user_role')
        return data


class UserMediaSerializer(RequestContextMixin, serializers.ModelSerializer):
    class Meta:
        model = UserMedia
        fields = (
            "id",
            "user",
            "media_type",
            "size",
            "extension",
            "file",
            "is_profile_photo",
            "created_time",
        )
        read_only_fields = ("id", "user", "media_type", "size", "extension", "created_time")

    def validate(self, data):
        """
        Validate the file size for PDFs
        """
        file = data.get("file")
        if file:
            if file.name.lower().endswith(".pdf"):
                if file.size > settings.MAX_PDF_SIZE_BYTES:
                    size_in_mb = file.size / (1024 * 1024)
                    raise_validation_error(
                        message=_(f"PDF files must be less than 10 MB. Current one is {size_in_mb:.2f}")
                    )
        return data


class UsersMeSerializer(serializers.ModelSerializer): # need to be updated
    media = UserMediaSerializer(many=True)
    educations = EducationSerializer(many=True, required=False)
    results = ResultCreateSerializer(many=True, required=False)
    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "pinfl",
            "phone_number",
            "email",
            "gender",
            "region",
            "district",
            "birth_date",
            "is_superuser",
            "media",
            "educations",
            "results",
            "user_role",
            "profile_photo",
            "is_verified",
            "created_time",
        ]
        read_only_fields = ["id", "created_time", "is_verified", "profile_photo"]

    def get_profile_photo(self, obj):
        """
        Returns the URL of the user's profile photo if it exists.
        """
        profile_photo = obj.media.filter(is_profile_photo=True).first()
        if profile_photo:
            return get_file_full_url(profile_photo.file.url)
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.user_role == "sportsman":
            data["sportsman_profile"] = SportsmanProfileSerializer(instance.sportsman_profile, context=self.context).data
        elif instance.user_role == "trainer":
            data["trainer_profile"] = TrainerProfileSerializer(instance.trainer_profile, context=self.context).data
        elif instance.user_role == "federation":
            data["federation"] = {
                "id": instance.federation.id,
                "name": instance.federation.name,
                "logo": get_file_full_url(instance.federation.logo.url) if instance.federation.logo else None
            } if instance.federation else None
        elif instance.user_role == "sport_institution_admin":
            data["sport_institution"] = {
                "id": instance.sport_institution.id,
                "name": instance.sport_institution.name,
            }
        data["region"] = {
            "id": instance.region.id,
            "name": instance.region.name
        } if instance.region else None
        data["district"] = {
            "id": instance.district.id,
            "name": instance.district.name
        } if instance.district else None
        return data


class SportsmanListSerializer(serializers.ModelSerializer):
    statistics = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "user_role",
            "statistics"
        ]

    def to_representation(self, instance: User) -> dict:
        data = super().to_representation(instance)
        if instance.sportsman_profile.sport:
            data["sport"] = instance.sportsman_profile.sport.name
            if instance.sportsman_profile.sport.logo:
                data["logo"] = get_file_full_url(instance.sportsman_profile.sport.logo.url) if instance.sportsman_profile.sport.logo else None
        if instance.sportsman_profile.trainer:
            data["trainer_id"] = instance.sportsman_profile.trainer.user_id
            data["trainer_name"] = f'{instance.sportsman_profile.trainer.user}'
        if getattr(instance, "sportsman_profile", None):
            data["points"] = instance.sportsman_profile.points
        if instance.profile_photo:
            data["profile_photo"] = get_file_full_url(instance.profile_photo.file.url)
        return data

    def get_statistics(self, obj) -> Dict[str, Any]:
        return {
            "total_gold": getattr(obj, "total_gold", 0),
            "total_silver": getattr(obj, "total_silver", 0),
            "total_bronze": getattr(obj, "total_bronze", 0),
            "total_competitions": getattr(obj, "total_competitions", 0),
        }


class SportsmanProfileSerializer(RequestContextMixin, serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True)
    trainer_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source="trainer", write_only=True, required=False)
    statistics = serializers.SerializerMethodField()
    send_request = serializers.BooleanField(required=True, write_only=True)
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)

    class Meta:
        model = Sportsman
        fields = [
            "sport_id",
            "trainer_id",
            "bio",
            "division",
            "sport_rank",
            "points",
            "user_metrics",
            "height",
            "weight",
            "address",
            "message",
            "social_media",
            "is_sportsman_verified",
            "is_result_paid",
            "statistics",
            "send_request"
        ]
        read_only_fields = ["is_sportsman_verified", "is_result_paid", "statistics"]

    def validate(self, attrs: dict) -> dict:
        height = attrs.get("height", None)
        weight = attrs.get("weight", None)
        sport = attrs.get("sport", None)
        trainer = attrs.get("trainer", None)
        if trainer and hasattr(trainer, "trainer_profile") and trainer.trainer_profile:
            trainer_profile = trainer.trainer_profile
            if not sport:
                raise_validation_error(message=_("Sport is required"))
            if trainer_profile.sport and trainer_profile.sport.id != sport.id:
                raise_validation_error(message=_(f"Trainer's sport must be equal to sportsman's sport"))

        return super().validate(attrs)

    def create(self, validated_data: dict) -> Sportsman:
        sport: Sport = validated_data.pop("sport", None)
        trainer: User = validated_data.pop("trainer", None)
        send_request: bool = validated_data.pop("send_request", False)
        validated_data.pop("message", None)

        profile = Sportsman.objects.create(sport=sport, trainer=trainer.trainer_profile, **validated_data)
        logger.info(f"Sportsman Profile created -> {profile}")

        return profile

    @transaction.atomic
    def update(self, instance: Sportsman, validated_data: dict) -> Sportsman:
        sender, new_trainer, old_trainer, message_from_sender, sportsman_data, request_type, send_request = \
        self._extract_update_data(instance, validated_data)

        if send_request and new_trainer:
            old_snapshot, new_snapshot, sportsman_data = self._handle_snapshot(instance, validated_data)
            if old_trainer != new_trainer:
                old_snapshot = None  # Reset old snapshot if trainer is changing

            user_request, message, success = UserRequestService.create_request(
                sender=sender,
                receivers=User.objects.filter(id=new_trainer.id),
                request_type=request_type,
                old_data=old_snapshot,
                new_data=new_snapshot,
                message_from_sender=message_from_sender
            )
            if not success:
                raise_validation_error(message=message)

        elif new_trainer:
            instance.trainer = new_trainer.trainer_profile

        # Update other fields
        for attr, value in sportsman_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance

    def get_statistics(self, obj) -> Dict[str, Any]:
        return calculate_sportsman_statistics(sportsman=obj.user)

    def to_representation(self, instance: Sportsman) -> dict:
        data = super().to_representation(instance)
        data["sport"] = {
            "id": instance.sport.id,
            "name": instance.sport.name,
            "logo": get_file_full_url(instance.sport.logo.url) if instance.sport.logo else None
        } if instance.sport else None
        data["trainer"] = {
            "id": instance.trainer.user_id,
            "name": f'{instance.trainer.user}',
            "sport": instance.trainer.sport.name if instance.trainer.sport else None,
            "full_name": instance.trainer.user.full_name,
        } if instance.trainer else None
        data["federation"] = {
            "id": instance.trainer.federation.id,
            "name": instance.trainer.federation.name,
            "logo": get_file_full_url(instance.trainer.federation.logo.url) if instance.trainer.federation.logo else None
        } if instance.trainer and instance.trainer.federation else None
        data["sport_rank"] = _(instance.sport_rank) if instance.sport_rank else None
        return data

    # ----------------------------
    # Helpers
    # ----------------------------
    def _filter_critical_fields(self, data: dict, critical_fields: list[str]) -> dict:
        filtered = {}
        for k, v in data.items():
            if isinstance(v, dict):
                # Recursively filter nested dictionaries
                filtered[k] = self._filter_critical_fields(v, critical_fields)
            elif k not in critical_fields:
                filtered[k] = v
        return filtered

    def _check_critical_fields(self, instance: Sportsman, data: dict) -> bool:
        critical_fields: list[str] = SPORTSMAN_APPROVAL_REQUIRED_FIELDS
        changed: bool = False
        sender: User = self.context.get("request").user  # type: ignore

        changed = any(
            field in data and getattr(instance, field) != data[field]
            for field in critical_fields
        )

        # If the sender is admin/super_admin, always return False
        if sender.user_role in ["admin", "super_admin"]:
            return False
        # If the sender is sportsman and fields have changed, return True
        elif changed and sender.user_role == "sportsman":
            return True
        return False

    def _handle_snapshot(
        self,
        instance: Sportsman,
        sportsman_data: dict,
    ) -> tuple[dict | None, dict | None, dict | None]:
        critical_fields = SPORTSMAN_APPROVAL_REQUIRED_FIELDS

        old_snapshot, new_snapshot = SnapshotService.build_snapshot(
            model=instance,
            data=sportsman_data,
            request_type=enums.UserRequestTypes.SPORTSMAN_TRAINER_REQUEST.value
        )
        sportsman_data = self._filter_critical_fields(sportsman_data, critical_fields)

        return old_snapshot, new_snapshot, sportsman_data

    def _extract_update_data(self, instance: Sportsman, validated_data: dict) -> tuple:
        """
        Extracts and prepares the necessary fields from validated_data.
        Returns: (sender, new_trainer, old_trainer, message_from_sender, sportsman_data, request_type)
        """
        sender: User = self.request.user  # type: ignore
        new_trainer: User | None = validated_data.get("trainer")
        old_trainer: User | None = instance.trainer.user if instance.trainer else None
        validated_data.pop("send_request", None)
        message_from_sender: str | None = validated_data.pop("message", None)
        sportsman_data: dict = validated_data
        request_type = enums.UserRequestTypes.SPORTSMAN_TRAINER_REQUEST.value
        send_request: bool = self._check_critical_fields(instance=instance, data=sportsman_data)
        return sender, new_trainer, old_trainer, message_from_sender, sportsman_data, request_type, send_request


class TrainerListSerializer(serializers.ModelSerializer):
    statistics = serializers.SerializerMethodField()
    # logo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "user_role",
            "statistics",
            # "logo",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.trainer_profile.sport:
            data["sport"] = instance.trainer_profile.sport.name
            if instance.trainer_profile.sport.logo:
                data["logo"] = get_file_full_url(instance.trainer_profile.sport.logo.url) if instance.trainer_profile.sport.logo else None
        if getattr(instance, "trainer_profile", None):
            data["points"] = instance.trainer_profile.points
        if instance.profile_photo:
            data["profile_photo"] = get_file_full_url(instance.profile_photo.file.url)
        return data

    def get_statistics(self, obj) ->  List[Dict[str, Any]]:
        stats = {
            "own_statistics": {
                "gold": obj.own_total_gold,
                "silver": obj.own_total_silver,
                "bronze": obj.own_total_bronze,
            },
            "students_statistics": {
                "gold": obj.students_total_gold,
                "silver": obj.students_total_silver,
                "bronze": obj.students_total_bronze,
            },
            "total_statistics": {
                "gold": obj.own_total_gold + obj.students_total_gold,
                "silver": obj.own_total_silver + obj.students_total_silver,
                "bronze": obj.own_total_bronze + obj.students_total_bronze,
            },
        }
        return stats


class TrainerProfileSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True)
    statistics = serializers.SerializerMethodField()
    send_request = serializers.BooleanField(required=True, write_only=True)
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)

    class Meta:
        model = Trainer
        fields = [
            "sport_id",
            "federation",
            "skill_level",
            "bio",
            "division",
            "user_metrics",
            "height",
            "weight",
            "points",
            "address",
            "message",
            "social_media",
            "is_trainer_verified",
            "statistics",
            "send_request"
        ]
        read_only_fields = ["is_trainer_verified", "statistics"]

    def validate(self, attrs: dict) -> dict:
        sport = attrs.get("sport", None)
        send_request = attrs.get("send_request", None)
        federation = attrs.get("federation", None)
        if not sport:
            raise_validation_error(message=_("Sport is required."))
        if send_request and not federation:
            raise_validation_error(message=_("Federation is required to send request."))
        if sport not in federation.sports.all():
            raise_validation_error(message=_("Sport must be part of the federation sports."))
        return super().validate(attrs)

    def create(self, validated_data: dict) -> Trainer:
        sport: Sport = validated_data.pop("sport", None)

        profile = Trainer.objects.create(sport=sport, **validated_data)
        logger.info(f"Trainer Profile created -> {profile}")

        return profile

    @transaction.atomic
    def update(self, instance: Trainer, validated_data: dict) -> Trainer:
        sender, trainer_data, new_federation, old_federation, send_request, message_from_sender, request_type, receivers = \
        self._extract_update_data(instance, validated_data)

        if send_request and new_federation:
            # TODO(CoderB7): change receivers filtering logic after applying RBAC to system
            old_snapshot, new_snapshot, trainer_data = self._handle_snapshot(instance, validated_data)
            if old_federation != new_federation:
                old_snapshot = None # Reset old snapshot if federation is changing

            user_request, message, success = UserRequestService.create_request(
                sender=sender,
                receivers=receivers,
                request_type=request_type,
                federation=new_federation,
                old_data=old_snapshot,
                new_data=new_snapshot,
                message_from_sender=message_from_sender
            )
            if not success:
                raise_validation_error(message=message)

        elif new_federation:
            instance.federation = new_federation

        # Update other fields
        for attr, value in trainer_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance

    def get_statistics(self, obj) -> Dict[str, Any]:
        return calculate_trainer_statistics(trainer=obj.user)

    def to_representation(self, instance: Trainer) -> dict:
        data = super().to_representation(instance)
        data["sport"] = {
            "id": instance.sport.id,
            "name": instance.sport.name,
            "logo": get_file_full_url(instance.sport.logo.url) if instance.sport.logo else None
        } if instance.sport else None
        data["federation"] = {
            "id": instance.federation.id,
            "name": instance.federation.name,
            "logo": get_file_full_url(instance.federation.logo.url) if instance.federation.logo else None
        } if instance.federation else None
        return data

    # ----------------------------
    # Helpers
    # ----------------------------
    def _filter_critical_fields(self, data: dict, critical_fields: list[str]) -> dict:
        filtered = {}
        for k, v in data.items():
            if isinstance(v, dict):
                # Recursively filter nested dictionaries
                filtered[k] = self._filter_critical_fields(v, critical_fields)
            elif k not in critical_fields:
                filtered[k] = v
        return filtered

    def _check_critical_fields(self, instance: Trainer, data: dict) -> bool:
        critical_fields: list[str] = TRAINER_APPROVAL_REQUIRED_FIELDS
        changed: bool = False
        sender: User = self.context.get("request").user  # type: ignore

        changed = any(
            field in data and getattr(instance, field) != data[field]
            for field in critical_fields
        )
        # If sender is admin/super_admin, always return False
        if sender.user_role in ["admin", "super_admin"]:
            return False
        # If sender is trainer and fields have changed, return True
        elif changed and sender.user_role == "trainer":
            return True
        return False

    def _handle_snapshot(
        self,
        instance: Trainer,
        trainer_data: dict,
    ) -> tuple[dict | None, dict | None, dict | None]:
        critical_fields: list[str] = TRAINER_APPROVAL_REQUIRED_FIELDS

        old_snapshot, new_snapshot = SnapshotService.build_snapshot(
            model=instance,
            data=trainer_data,
            request_type=enums.UserRequestTypes.TRAINER_FEDERATION_REQUEST.value
        )
        trainer_data = self._filter_critical_fields(trainer_data, critical_fields)

        return old_snapshot, new_snapshot, trainer_data

    def _extract_update_data(self, instance: Trainer, validated_data: dict) -> tuple[dict, Federation | None, bool, str | None]:
        """
        Extracts and prepares trainer update-related data for the update method.
        Returns: (trainer_data, new_federation, send_request, message_from_sender)
        """
        sender: User = self.context.get("request").user  # type: ignore
        new_federation: Federation = validated_data.get("federation")
        old_federation = instance.federation
        validated_data.pop("send_request", None)
        message_from_sender: str | None = validated_data.pop("message", None)
        trainer_data: dict = validated_data
        send_request: bool = self._check_critical_fields(instance=instance, data=trainer_data)
        request_type: str = enums.UserRequestTypes.TRAINER_FEDERATION_REQUEST.value
        receivers: QuerySet[User] = new_federation.users.filter(user_role="federation")
        return sender, trainer_data, new_federation, old_federation, send_request, message_from_sender, request_type, receivers


class RegistrationSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True, required=True)
    results = ResultCreateSerializer(many=True, required=True)
    sportsman_profile = SportsmanProfileSerializer(required=False)
    trainer_profile = TrainerProfileSerializer(required=False)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    media = UserMediaSerializer(many=True, required=False, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "first_name",
            "middle_name",
            "last_name",
            "pinfl",
            "gender",
            "region",
            "district",
            "user_role",
            "email",
            "media_ids",
            "media",
            "birth_date",
            "user_role",
            "educations",
            "results",
            "is_verified",
            "sportsman_profile",
            "trainer_profile",
            "created_time",
        )
        extra_kwargs = {
            "id": {"read_only": True},
            "is_verified": {"read_only": True},
            "media_ids": {"required": False},
            }

    def validate(self, attrs):
        pinfl = attrs.get("pinfl", None)
        user_role = attrs.get("user_role")

        phone_number = attrs.get("phone_number")
        if phone_number:
            if User.objects.only("id").filter(phone_number=phone_number).exists() :
                raise_validation_error(message=_("Phone number is already registered"))

        if user_role != "ordinary":
            if pinfl:
                if User.objects.only("id").filter(pinfl=pinfl).exists():
                    raise_validation_error(message=_("PINFL is already registered"))
                if not pinfl.isdigit():
                    raise_validation_error(message=_("PINFL must contain only numbers."))
                if len(pinfl) != 14:
                    raise_validation_error(message=_("PINFL must be exactly 14 digits."))
            else:
                raise_validation_error(message=_("PINFL is required"))

        return attrs

    def create(self, validated_data):
        educations_data = validated_data.pop("educations", None)
        results_data = validated_data.pop("results", None)
        user_role = validated_data.get("user_role")
        sportsman_profile_data = validated_data.pop("sportsman_profile", None)
        trainer_profile_data = validated_data.pop("trainer_profile", None)
        media_ids = validated_data.pop("media_ids", None)

        with transaction.atomic():
            user = User.objects.create(**validated_data)
            # if media_ids:
            #     media_objects = UserMedia.objects.filter(id__in=media_ids)

            #     if not media_objects.exists():
            #         raise_validation_error(message=_(f"At least one media must be uploaded"))

            #     media_objects.update(user=user) # view in sql
            if media_ids:
                media_objects = list(UserMedia.objects.filter(id__in=media_ids))  # Convert to list to avoid multiple queries
                if not media_objects:
                    raise_validation_error(message=_("At least one media must be uploaded"))

                for media in media_objects:
                    media.user = user
                UserMedia.objects.bulk_update(media_objects, ["user"])

            # Bulk create educations
            if educations_data:
                Education.objects.bulk_create([
                    Education(user=user, **ed_data) for ed_data in educations_data
                ])

            # create() inside the loop, because has to trigger signal!
            for result_data in results_data:
                if 'archived_trainer_name' in result_data:
                    archived_trainer_name = result_data.pop('archived_trainer_name')
                    if archived_trainer_name:
                        ArchivedTrainerSerializer().validate(attrs={"name": archived_trainer_name})
                        archived_trainer = ArchivedTrainer.objects.create(name=archived_trainer_name)
                        result_data['archived_trainer'] = archived_trainer
                Result.objects.create(user=user, **result_data)

            if user_role == "sportsman" and sportsman_profile_data:
                sportsman_profile_data.pop("send_request", None)
                sportsman_profile_data['trainer'] = sportsman_profile_data.get('trainer').trainer_profile
                Sportsman.objects.create(user=user, **sportsman_profile_data)
            elif user_role == "trainer" and trainer_profile_data:
                trainer_profile_data.pop("send_request", None)
                Trainer.objects.create(user=user, **trainer_profile_data)

            logger.info(f"User created -> {user}")
            return user

    def get_tokens(self, user):  # noqa
        return user.tokens()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data["user_role"] == "ordinary":
            data["tokens"] = self.get_tokens(instance)
        data["region"] = {
            "id": instance.region.id,
            "name": instance.region.name
        } if instance.region else None
        data["district"] = {
            "id": instance.district.id,
            "name": instance.district.name
        } if instance.district else None

        # Remove empty profiles
        if getattr(instance, "sportsman_profile", None) is None:
            data.pop("sportsman_profile")
        if getattr(instance, "trainer_profile", None) is None:
            data.pop("trainer_profile")

        return data


class SelfRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for self-registration of users.
    """
    tokens = serializers.SerializerMethodField()
    fcm_token = serializers.CharField(required=False)
    device_type = serializers.ChoiceField(choices=DeviceType.choices, required=False)
    federation = serializers.PrimaryKeyRelatedField(
        queryset=Federation.objects.all(),
        required=False
    )
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)

    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "first_name",
            "middle_name",
            "last_name",
            "birth_date",
            "email",
            "user_role",
            "federation",
            "message",
            "is_verified",
            "fcm_token",
            "device_type",
            "tokens",
            "created_time"
        )
        read_only_fields = ["id", "is_verified", "created_time"]

    def validate(self, attrs: dict) -> dict:
        phone_number = attrs.get("phone_number")
        first_name = attrs.get("first_name")
        last_name = attrs.get("last_name")
        if phone_number:
            if User.objects.only("id").filter(phone_number=phone_number).exists() :
                raise_validation_error(message=_("Phone number is already registered"))

        if User.objects.only("id").filter(
            first_name=first_name, last_name=last_name, phone_number=phone_number
        ).exists():
            raise_validation_error(message=_("User with this name and phone number already exists"))

        return attrs

    def create(self, validated_data: dict) -> User:
        fcm_token = validated_data.pop("fcm_token", None)
        device_type = validated_data.pop("device_type", None)
        federation = validated_data.pop("federation", None)
        message_from_sender: str | None = validated_data.pop("message", None)
        with transaction.atomic():
            user: User = super().create(validated_data)
            user_role = validated_data.get("user_role")
            if fcm_token:
                FCMDevice.objects.update_or_create(
                    registration_id=fcm_token,
                    defaults={
                        'user': user,
                        'type': device_type,
                        'active': True,
                    }
                )
            if user_role == "sportsman":
                Sportsman.objects.create(user=user)
            elif user_role == "trainer":
                Trainer.objects.create(user=user)
            elif user_role == "federation":
                if federation:
                    logger.info(f"Federation '{federation.name}' selected for user {user.first_name} {user.last_name}")
                    request_type: str = enums.UserRequestTypes.FEDERATION_ADMIN_REQUEST.value
                    receivers: QuerySet[User] = federation.users.all()
                    old_snapshot, new_snapshot = SnapshotService.build_snapshot(
                        model=user,
                        request_type=request_type
                    )
                    logger.info(new_snapshot)
                    user_request, message, success = UserRequestService.create_request(
                        sender=user,
                        receivers=receivers,
                        request_type=request_type,
                        federation=federation,
                        old_data={},
                        new_data=new_snapshot,
                        message_from_sender=message_from_sender
                    )
                    if not success:
                        raise_validation_error(message=message)
            logger.info(f"User created -> {user}")
            return user

    def get_tokens(self, user): # noqa
        if not user:
            return None
        return user.tokens()


class LogoutSerializer(serializers.Serializer):  # noqa
    refresh = serializers.CharField(required=True)
    fcm_token = serializers.CharField(required=False)


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        # Check if new password matches the confirmation
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")
        if new_password != confirm_password:
            raise_validation_error(message=_("New password don't match"))

        return attrs

    def update(self, instance, validated_data):
        # Set the new password
        new_password = validated_data["new_password"]
        instance.set_password(new_password)
        instance.save()
        return validated_data


class UpdatePhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15, required=True)
    password = serializers.CharField(max_length=128, required=True)
    confirm_password = serializers.CharField(max_length=128, required=True)

    def validate(self, value):
        request_context = self.context.get("request")
        user = request_context.user if request_context is not None else None

        # Check if all required fields are present in the request body
        if (
            not value.get("phone_number")
            or not value.get("password")
            or not value.get("confirm_password")
        ):
            raise_validation_error(message=_("All required fields must be present"))
        # check if phone number equals to user existing phone number
        if user.phone_number == value.get("phone_number"):
            raise_validation_error(message=_("You entered your current phone number!"))

        if User.objects.filter(phone_number=value.get("phone_number")).exists():
            raise_validation_error(message=_("Phone number is already registered"))

        # Check if the password and confirm_password fields match
        if value.get("password") != value.get("confirm_password"):
            raise_validation_error(message=_("Passwords do not match"))

        # Authenticate the user based on their password
        auth_user = authenticate(username=user.username, password=value.get("password"))
        if not auth_user:
            raise_validation_error(message=_("Invalid password"))
        return value


class CustomTokenRefreshSerializer(jwt_serializers.TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        access_token_instance = jwt_tokens.AccessToken(data["access"])
        user_id = access_token_instance["user_id"]
        user = get_object_or_404(User, id=user_id)
        update_last_login(None, user)
        return data


class UserUpdateSerializer(serializers.ModelSerializer):
    sportsman_profile = SportsmanProfileSerializer(required=False)
    trainer_profile = TrainerProfileSerializer(required=False)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    media = UserMediaSerializer(many=True, required=False)
    educations = EducationSerializer(many=True, required=False)
    results = ResultCreateSerializer(many=True, required=False)
    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "pinfl",
            "phone_number",
            "gender",
            "region",
            "district",
            "email",
            "birth_date",
            "media_ids",
            "media",
            "user_role",
            "educations",
            "results",
            "profile_photo",
            "sportsman_profile",
            "trainer_profile",
            "created_time",
            "is_verified",
        ]
        read_only_fields = ["id", "created_time", "is_verified", "profile_photo"]

    def get_profile_photo(self, obj):
        """
        Returns the URL of the user's profile photo if it exists.
        """
        profile_photo = self.instance.media.filter(is_profile_photo=True).first()
        if profile_photo:
            return get_file_full_url(profile_photo.file.url)
        return None

    def _extract_nested_data(self, validated_data: dict) -> tuple[dict, dict, dict]:
        sportsman_data = validated_data.pop("sportsman_profile", {}) or {}
        trainer_data = validated_data.pop("trainer_profile", {}) or {}
        return validated_data, sportsman_data, trainer_data

    def validate(self, attrs: dict) -> dict:
        phone_number = attrs.get("phone_number")
        pinfl = attrs.get("pinfl", None)
        user_role = attrs.get("user_role")
        instance: User = t.cast(User, self.instance)

        # Checking if phone_number is being updated
        if phone_number and instance.phone_number != phone_number:
            # Looking for other users with the same phone number
            if User.objects.filter(phone_number=phone_number).exists():
                raise_validation_error(message=_("Phone number is already registered"))

        if user_role != "ordinary":
            if pinfl:
                if instance.pinfl != pinfl:
                    if User.objects.filter(pinfl=pinfl).exists():
                        raise_validation_error(message=_("PINFL is already registered"))
                if not pinfl.isdigit():
                    raise_validation_error(message=_("PINFL must contain only numbers."))
                if len(pinfl) != 14:
                    raise_validation_error(message=_("PINFL must be exactly 14 digits."))

        return attrs

    def update(self, instance: User, validated_data: dict) -> User:
        educations_data = validated_data.pop("educations", None)
        results_data = validated_data.pop("results", None)
        media_ids = validated_data.pop("media_ids", None)

        # Extract user, sportsman, and trainer data
        user_data, sportsman_data, trainer_data = self._extract_nested_data(validated_data)

        with transaction.atomic():
            # Performing actual updates on allowed fields
            for attr, value in user_data.items():
                setattr(instance, attr, value)
            instance.save()

            if media_ids:
                media_objects = UserMedia.objects.filter(id__in=media_ids)

                if not media_objects.exists():
                    raise_validation_error(message=_("At least one media must be uploaded"))

                current_media = instance.media.all() # Get current media
                media_to_delete = current_media.exclude(id__in=media_ids)

                for media in media_to_delete:
                    media.file.delete()  # Delete the file from the file system
                    media.delete()  # Delete the Media object from the database

                # Associate the new media objects
                media_objects.update(user=instance)
            else:
                # If media_ids is None, remove all existing media associations
                current_media = instance.media.all()
                for media in current_media:
                    media.file.delete()  # Delete the file from the file system
                    media.delete()  # Delete the Media object from the database

            if educations_data:
                instance.educations.all().delete()
                for education_data in educations_data:
                    Education.objects.create(user=instance, **education_data)

            if results_data:
                instance.results.all().delete()
                for result_data in results_data:
                    if 'archived_trainer_name' in result_data:
                        archived_trainer_name = result_data.pop('archived_trainer_name')
                        if archived_trainer_name:
                            ArchivedTrainerSerializer().validate(attrs={"name": archived_trainer_name})
                            archived_trainer = ArchivedTrainer.objects.create(name=archived_trainer_name)
                            result_data['archived_trainer'] = archived_trainer
                    Result.objects.create(user=instance, **result_data)

            if sportsman_data:
                sportsman_profile = getattr(instance, "sportsman_profile", None)
                if sportsman_profile:
                    SportsmanProfileSerializer(
                        context={
                            "request": self.context.get("request"),
                        }
                    ).update(sportsman_profile, sportsman_data)

            if trainer_data:
                trainer_profile = getattr(instance, "trainer_profile", None)
                if trainer_profile:
                    TrainerProfileSerializer(
                        context={
                            "request": self.context.get("request"),
                        }
                    ).update(trainer_profile, trainer_data)

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["region"] = {
            "id": instance.region.id,
            "name": instance.region.name,
        } if instance.region.id else None
        data["district"] = {
            "id": instance.district.id,
            "name": instance.district.name,
        } if instance.district.id else None
        # Remove empty profiles
        if getattr(instance, "sportsman_profile", None) is None:
            data.pop("sportsman_profile", None)
        if getattr(instance, "trainer_profile", None) is None:
            data.pop("trainer_profile", None)
        return data


class ArchivedTrainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivedTrainer
        fields = ["id", "name"]
        extra_kwargs = {"id": {"read_only": True}}

    def validate(self, attrs):
        name = attrs.get('name', None)

        if name:
            if ArchivedTrainer.objects.filter(name=name).exists():
                raise_validation_error(message=_("Archived Trainer with this name already exists"))

        return attrs


class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = [
            "id",
            "title",
            "text",
            "is_read",
            "data",
            "created_time",
            "updated_time",
        ]
        read_only_fields = ["id", "created_time", "updated_time"]


class UserRequestSerializer(RequestContextMixin, serializers.ModelSerializer):
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

    def validate(self, attrs: dict) -> dict:
        request_type = attrs.get("request_type")
        sender = t.cast(User, self.request.user)
        if request_type == "sportsman_trainer_request" and sender.user_role == "trainer":
            raise_validation_error(message=_("Trainers cannot send trainer requests!"))
        return super().validate(attrs)

    def create(self, validated_data: dict) -> t.Optional[UserRequest]:
        sender = self.request.user  # type: ignore
        logger.info(f"Sender: {sender}")
        user_request: None = None

        #TODO(CoderB7): implement logic of sending request if needed in some cases
        return user_request

    def update(self, instance: UserRequest, validated_data: dict) -> UserRequest:
        sender: User = instance.sender
        logger.info(f"Sender: {sender}")  # LOGGING
        receiver: User = self.request.user  # type: ignore
        logger.info(f"New data: {instance.new_data}")  # LOGGING
        message, success = UserRequestService.handle_request(instance, validated_data, receiver)
        if success:
            logger.info(f"{message}")
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        else:
            logger.error(f"Failed to handle request: {message}")
            raise_validation_error(message=message)
        return instance

    def to_representation(self, instance: UserRequest) -> dict:
        data = super().to_representation(instance)
        receiver: User = instance.receivers.first()  # type: ignore
        data["sender"] = {
            "id": instance.sender.id,
            "full_name": instance.sender.full_name,
            "user_role": instance.sender.user_role,
            "phone_number": instance.sender.phone_number,
        }
        if instance.federation:
            federation: Federation = instance.federation
            logger.info(f"Federation: {federation}")
            data["receiver"] = {
                "federation": {
                    "id": federation.id,
                    "name": federation.name,
                    "phone_number": federation.phone_number,
                    "is_national": federation.is_national,
                } if federation else None
            }
            data["processed_by"] = {
                "federation": {
                    "id": federation.id,
                    "name": federation.name,
                    "phone_number": federation.phone_number,
                    "is_national": federation.is_national,
                } if federation else None
            }
        else:
            data["receiver"] = {
                "id": receiver.id,
                "full_name": receiver.full_name,
                "user_role": receiver.user_role,
                "phone_number": receiver.phone_number,
            }
            data["processed_by"] = {
                "id": instance.processed_by.id,
                "full_name": instance.processed_by.full_name,
                "phone_number": instance.processed_by.phone_number,
            } if instance.processed_by else None
        data["processed_time"] = instance.processed_time
        data.pop("receivers")
        return data


class SportsmanResultSerializer(RequestContextMixin, serializers.ModelSerializer):
    archived_trainer_name = serializers.CharField(max_length=255, required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)

    class Meta:
        model = Result
        fields = [
            "id",
            "country",
            "tournament",
            "trainer",
            "archived_trainer_name",
            "year",
            "currently_participating",
            "rating",
            "score",
            "message",
            "additional_attributes",
            "is_verified",
            "status",
            "gold",
            "silver",
            "bronze",
        ]
        read_only_fields = ["id", "is_verified", "gold", "silver", "bronze", "status", "score"]

    def validate(self, attrs: dict) -> dict:
        sportsman: User = self.request.user # type: ignore
        federation: Federation = sportsman.sportsman_profile.trainer.federation
        tournament = attrs.get("tournament", None)
        trainer = attrs.get("trainer", None)
        rating = attrs.get("rating", None)
        year = attrs.get("year", None)
        instance: Result = self.instance
        # if instance and tournament:
        #     if instance.tournament != tournament:
        #         raise_validation_error(message=_("You are not allowed to update a tournament of this result."))
        if Result.objects.filter(user=sportsman, tournament=tournament, trainer=trainer, year=year).exists():
            raise_validation_error(message=_("You have already submitted a result for this tournament and year."))
        if not trainer:
            raise_validation_error(message=_("You must specify a trainer to submit results."))
        if not federation:
            raise_validation_error(message=_("You must be part of a federation to submit results."))
        if federation and not federation.tournaments.filter(id=tournament.id).exists():
            raise_validation_error(message=_("You are not allowed to submit results for this tournament."))
        if trainer and not federation.trainers.filter(user_id=trainer.pk).exists():
            raise_validation_error(message=_("You are not allowed to submit results for this trainer."))
        if rating and not tournament.scoring_policies.filter(position=rating).exists():
            raise_validation_error(message=_("Invalid rating for this tournament."))
        if instance and Result.objects.exclude(pk=instance.pk).filter(user=sportsman, tournament=tournament, trainer=trainer, year=year).exists():
            raise_validation_error(message=_("You have already submitted a result for this tournament and year."))
        if UserRequest.objects.filter(
            sender=sportsman,
            status=enums.UserRequestStatus.PENDING.value,
            request_type=enums.UserRequestTypes.SPORTSMAN_RESULT_VERIFICATION_REQUEST.value,
            federation=federation,
        ).exists():
            raise_validation_error(message=_("You already have a pending request!"))
        return attrs

    # def create(self, validated_data: dict) -> Result:
    #     sender: User = self.request.user  # type: ignore
    #     result = self._save_result(sender, validated_data)
    #     return result

    def create(self, validated_data: dict) -> t.Union[Result, UserRequest]:
        sender: User = self.request.user  # type: ignore
        message_from_sender: str | None = validated_data.pop("message", None)
        archived_trainer_name: str | None = validated_data.pop("archived_trainer_name", None)

        if archived_trainer_name:
            archived_trainer = ArchivedTrainer.objects.create(name=archived_trainer_name)
            result = Result.objects.create(user=sender, archived_trainer=archived_trainer, **validated_data)
            return result

        tournament: Tournament = validated_data.get("tournament")
        score = tournament.get_score(validated_data.get("rating")) if tournament else None
        validated_data['score'] = score
        trainer: User = validated_data.get("trainer")

        new_snapshot: dict = SportsmanResultSnapshotSerializer().to_new_snapshot(validated_data)

        user_request, message, success = UserRequestService.create_request(
            sender=sender,
            receivers=User.objects.filter(id=trainer.user_id),
            request_type=enums.UserRequestTypes.SPORTSMAN_RESULT_VERIFICATION_REQUEST.value,
            old_data={},
            new_data=new_snapshot,
            message_from_sender=message_from_sender
        )
        if not success:
            raise_validation_error(message=message)

        return user_request

    def _save_result(self, sender, validated_data):
        new_trainer = validated_data.pop("trainer", None)
        archived_trainer_name = validated_data.pop("archived_trainer_name", None)
        message_from_sender = validated_data.pop("message", None)

        # Handle archived trainer case
        if archived_trainer_name:
            return self._handle_archived_trainer(sender, archived_trainer_name, validated_data)

        # Handle trainer case (with snapshot + request if needed)
        return self._handle_trainer(sender, new_trainer, validated_data, message_from_sender)

    def _handle_archived_trainer(self, sender, archived_trainer_name, validated_data):
        archived_trainer = ArchivedTrainer.objects.create(name=archived_trainer_name)
        result = Result.objects.create(user=sender, archived_trainer=archived_trainer, **validated_data)
        return result

    @transaction.atomic
    def _handle_trainer(self, sender, new_trainer, validated_data, message_from_sender):
        rating = validated_data.pop("rating")
        tournament: Tournament = validated_data.get("tournament", None)
        score = tournament.get_score(rating) if tournament and rating else None
        result: Result = None

        if new_trainer:
            result = Result.objects.create(user=sender, **validated_data)
            _, new_snapshot, result_data = self._handle_snapshot(result, validated_data)

            # Create result first
            new_snapshot['score'] = str(score)
            new_snapshot['id'] = str(result.id)
            new_snapshot['rating'] = str(rating)

            logger.info(f"New Snapshot: {new_snapshot}")  # LOGGING
            # Create verification request
            request_type = enums.UserRequestTypes.SPORTSMAN_RESULT_VERIFICATION_REQUEST.value
            user_request, message, success = UserRequestService.create_request(
                sender=sender,
                receivers=User.objects.filter(id=new_trainer.user.id),
                request_type=request_type,
                old_data={},
                new_data=new_snapshot,
                message_from_sender=message_from_sender
            )
            if not success:
                raise_validation_error(message=message)

            return result

    def to_representation(self, instance: Result) -> t.Optional[dict]:
        if isinstance(instance, UserRequest):
            return UserRequestSerializer(instance).data
        data = super().to_representation(instance)
        data["tournament"] = {
            "id": instance.tournament.id,
            "name": instance.tournament.name,
            "logo": get_file_full_url(instance.tournament.logo.url) if instance.tournament.logo else None,
        } if instance.tournament else None
        data["trainer"] = {
            "id": instance.trainer.user.id,
            "full_name": instance.trainer.user.full_name,
            "phone_number": instance.trainer.user.phone_number,
        } if instance.trainer else None
        data["archived_trainer"] = {
            "id": instance.archived_trainer.id,
            "name": instance.archived_trainer.name,
        } if instance.archived_trainer else None
        return data

    # ----------------------------
    # Helpers
    # ----------------------------
    def _filter_critical_fields(self, data: dict, critical_fields: list[str]) -> dict:
        filtered = {}
        for k, v in data.items():
            if isinstance(v, dict):
                # Recursively filter nested dictionaries
                filtered[k] = self._filter_critical_fields(v, critical_fields)
            elif k not in critical_fields:
                filtered[k] = v
        return filtered

    def _handle_snapshot(
        self,
        instance: Result,
        result_data: dict
    ) -> tuple[dict | None, dict | None, dict | None]:
        critical_fields = SPORTSMAN_RESULT_APPROVAL_REQUIRED_FIELDS

        old_snapshot, new_snapshot = SnapshotService.build_snapshot(
            model=instance,
            data=result_data,
            request_type=enums.UserRequestTypes.SPORTSMAN_RESULT_VERIFICATION_REQUEST.value
        )
        result_data = self._filter_critical_fields(result_data, critical_fields)

        return old_snapshot, new_snapshot, result_data


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = [
            "id",
            "name"
        ]


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = [
            "id",
            "name",
            "region"
        ]


class NeighborhoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Neighborhood
        fields = [
            "id",
            "name",
            "district"
        ]
