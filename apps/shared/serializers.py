import decimal
import typing as t
import os

from datetime import date

import rest_framework_simplejwt.serializers as jwt_serializers
import rest_framework_simplejwt.tokens as jwt_tokens
from rest_framework.generics import get_object_or_404
from rest_framework import serializers

from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.shared.utils.enums import SportRankEnum
from apps.shared.utils.logging import logger
from apps.federation.models import Federation, FederationAgeGroup
from apps.sport.models import Sport, Tournament, SportInstitution
from apps.user.models import User, Trainer, Sportsman, TemporaryFile
from apps.shared.utils.mixins import RequestContextMixin
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.general import get_file_full_url


class BaseMediaSerializer(RequestContextMixin, serializers.ModelSerializer):
    class Meta:
        abstract = True

    def _file_validator(self, file) -> None:
        if file.size > settings.MAX_DOCUMENT_SIZE_BYTES:
            size_in_mb = file.size / (1024 * 1024)
            raise_validation_error(
                message=(
                    f"Document files must be less than {settings.MAX_DOCUMENT_SIZE_BYTES / (1024 * 1024):.0f} MB."
                    f" Current one is {size_in_mb:.2f} MB."
                )
            )

    def _image_validator(self, file) -> None:
        if file.size > settings.MAX_IMAGE_SIZE_BYTES:
            size_in_mb = file.size / (1024 * 1024)
            raise_validation_error(
                message=(
                    f"Image files must be less than {settings.MAX_IMAGE_SIZE_BYTES / (1024 * 1024):.0f} MB."
                    f" Current one is {size_in_mb:.2f} MB."
                )
            )

    def _video_validator(self, file) -> None:
        if file.size > settings.MAX_VIDEO_SIZE_BYTES:
            size_in_mb = file.size / (1024 * 1024)
            raise_validation_error(
                message=(
                    f"Video files must be less than {settings.MAX_VIDEO_SIZE_BYTES / (1024 * 1024):.0f} MB."
                    f" Current one is {size_in_mb:.2f} MB."
                )
            )

    def validate(self, data):
        """
        Validate uploaded file type and size.
        Works for all subclasses that define a `file` field.
        """
        file = data.get("file")

        if not file:
            raise_validation_error(message=("File is required"))

        file_name = file.name.lower()
        _, ext = os.path.splitext(file_name)

        if ext in settings.DOCUMENT_TYPES:
            self._file_validator(file)
        elif ext in settings.IMAGE_TYPES:
            self._image_validator(file)
        elif ext in settings.VIDEO_TYPES:
            self._video_validator(file)
        else:
            raise_validation_error(
                message=(
                    f"Unsupported file type " + ext
                )
            )
        return data


# -- Sportsman Result Approval Snapshot Serializers --
class SportsmanResultSnapshotSerializer(serializers.Serializer):
    country = serializers.CharField(required=False, allow_null=True)
    year = serializers.IntegerField(required=False, allow_null=True)
    age_group = serializers.PrimaryKeyRelatedField(queryset=FederationAgeGroup.objects.all(), required=False, allow_null=True)
    weight = serializers.CharField(required=False, allow_null=True, max_length=10)
    rating = serializers.IntegerField(required=False, allow_null=True)
    tournament = serializers.PrimaryKeyRelatedField(queryset=Tournament.objects.all(), required=True)
    score = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    temp_file = serializers.PrimaryKeyRelatedField(queryset=TemporaryFile.objects.all(), required=False, allow_null=True)

    def to_internal_value(self, data: dict[str, t.Any]) -> dict[str, t.Any]:
        """
        Allow deserialization from both:
        - {"tournament": "uuid", "age_group": "uuid", ..., "temp_file": "uuid"}
        - {"tournament": {"id": "uuid", ...}, "age_group": {"id": "uuid", ...}, "temp_file": {"id": "uuid", ...}}
        """
        if isinstance(data.get("age_group"), dict):
            data["age_group"] = data["age_group"].get("id")
        if isinstance(data.get("tournament"), dict):
            data["tournament"] = data["tournament"].get("id")
        if isinstance(data.get("temp_file"), dict):
            data["temp_file"] = data["temp_file"].get("id")
        if isinstance(data.get("score"), str):
            try:
                data["score"] = decimal.Decimal(data["score"])
            except decimal.InvalidOperation:
                pass
        logger.debug(f"Deserialized Internal data: {data}")
        return super().to_internal_value(data)

    def to_new_snapshot(self, validated_data: dict) -> dict:
        tournament: Tournament = validated_data.get("tournament")
        age_group: FederationAgeGroup = validated_data.get("age_group")
        return {
            "tournament": {
                "id": str(tournament.id),
                "name": tournament.name
            } if tournament else None,
            "age_group": {
                "id": str(age_group.id),
                "name": age_group.age_group.name,
                "min_age": age_group.age_group.min_age,
                "max_age": age_group.age_group.max_age,
            } if age_group else None,
            "country": validated_data.get("country"),
            "year": validated_data.get("year"),
            "rating": validated_data.get("rating"),
            "score": str(validated_data.get("score")),
            "weight": validated_data.get("weight"),
            "temp_file": {
                "id": str(validated_data.get("temp_file").id),
                "file_url": get_file_full_url(validated_data.get("temp_file").file.url)
            } if validated_data.get("temp_file") else None
        }


# -- Trainer WorkPlace Snapshot Serializers --
class TrainerWorkPlaceSnapshotSerializer(serializers.Serializer):
    sport_institution = serializers.PrimaryKeyRelatedField(queryset=SportInstitution.objects.all(), required=True)
    sport = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), required=True)
    start_year = serializers.IntegerField(required=True)
    start_month = serializers.IntegerField(required=True)
    end_year = serializers.IntegerField(required=True)
    end_month = serializers.IntegerField(required=True)
    workload = serializers.FloatField(required=True)

    def to_internal_value(self, data: dict[str, t.Any]) -> dict[str, t.Any]:
        """
        Allow deserialization from both:
        - {"sport_institution": "uuid", "sport": "uuid"}
        - {"sport_institution": {"id": "uuid", ...}, "sport": {"id": "uuid", ...}}
        """
        if isinstance(data.get("sport_institution"), dict):
            data["sport_institution"] = data["sport_institution"].get("id")
        if isinstance(data.get("sport"), dict):
            data["sport"] = data["sport"].get("id")
        logger.debug(f"Deserialized Internal data: {data}")
        return super().to_internal_value(data)

    def to_new_snapshot(self, validated_data: dict) -> dict:
        sport_institution: SportInstitution = validated_data.get("sport_institution")
        sport: Sport = validated_data.get("sport")
        return {
            "sport_institution": {
                "id": str(sport_institution.id),
                "name": sport_institution.name
            } if sport_institution else None,
            "sport": {
                "id": str(sport.id),
                "name": sport.name
            } if sport else None,
            "start_year": validated_data.get("start_year"),
            "start_month": validated_data.get("start_month"),
            "end_year": validated_data.get("end_year"),
            "end_month": validated_data.get("end_month"),
            "workload": validated_data.get("workload"),
        }


class EducationSnapshotSerializer(serializers.Serializer):
    sport_institution = serializers.PrimaryKeyRelatedField(queryset=SportInstitution.objects.all(), required=True)
    sport = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), required=True)
    start_year = serializers.IntegerField(required=True)
    end_year = serializers.IntegerField(required=False, default=None, allow_null=True)
    currently_studying = serializers.BooleanField(default=False)

    def to_internal_value(self, data: dict[str, t.Any]) -> dict[str, t.Any]:
        """
        Allow deserialization from both:
        - {"sport_institution": "uuid", "sport": "uuid", "trainer": "uuid", ...}
        - {"sport_institution": {"id": "uuid", ...}, "sport": {"id": "uuid", ...}, "trainer": {"id": "uuid", ...}, ...}
        """
        if isinstance(data.get("sport_institution"), dict):
            data["sport_institution"] = data["sport_institution"].get("id")
        if isinstance(data.get("sport"), dict):
            data["sport"] = data["sport"].get("id")
        logger.debug(f"Deserialized Internal data: {data}")
        return super().to_internal_value(data)

    def to_new_snapshot(self, validated_data: dict) -> dict:
        sport_institution: SportInstitution = validated_data.get("sport_institution")
        sport: Sport = validated_data.get("sport")
        return {
            "sport_institution": {
                "id": str(sport_institution.id),
                "name": sport_institution.name,
                "phone_number": sport_institution.phone_number,
                "director": sport_institution.director,
                "type": sport_institution.type,
                "address": sport_institution.address,
            } if sport_institution else None,
            "sport": {
                "id": str(sport.id),
                "name": sport.name
            } if sport else None,
            "start_year": validated_data.get("start_year"),
            "end_year": validated_data.get("end_year"),
            "currently_studying": validated_data.get("currently_studying"),
        }


# -- Sportsman Approval Snapshot Serializers --
class SportsmanSnapshotSerializer(serializers.Serializer):
    """
    Snapshot serializer for Sportsman for approval requests.
    """
    height = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    weight = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    sport_rank = serializers.ChoiceField(choices=SportRankEnum.choices(), required=False, allow_null=True)
    sport = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), required=False, allow_null=True)
    trainer = serializers.PrimaryKeyRelatedField(queryset=Trainer.objects.all(), required=False, allow_null=True)

    def to_internal_value(self, data: dict[str, t.Any]) -> dict[str, t.Any]:
        """
        Allow deserialization from both:
        - {"sport": "uuid", "trainer": "uuid", ...}
        - {"sport": {"id": "uuid", ...}, "trainer": {"id": "uuid", ...}, ...}
        """
        if isinstance(data.get("sport"), dict):
            data["sport"] = data["sport"].get("id")
        if isinstance(data.get("trainer"), dict):
            data["trainer"] = data["trainer"].get("id")
        # logger.debug(f"Deserialized Internal data: {data}")
        return super().to_internal_value(data)

    def to_new_snapshot(self, validated_data: dict) -> dict:
        """
        Creates a snapshot of the new Sportsman data.
        """
        sport: Sport = validated_data.get("sport")
        trainer: Trainer = validated_data.get("trainer")
        return {
            "trainer": {
                "id": str(trainer.user_id),
                "full_name": trainer.user.full_name,
            } if trainer else None,
            "sport": {
                "id": str(sport.id),
                "name": sport.name
            },
            "height": str(validated_data.get("height")),
            "weight": str(validated_data.get("weight")),
            "sport_rank": validated_data.get("sport_rank"),
        }

    def to_old_snapshot(self, instance: Sportsman) -> dict:
        """
        Creates a snapshot of the old Sportsman data.
        """
        sport: Sport = instance.sport
        trainer: Trainer = instance.trainer
        return {
            "trainer": {
                "id": str(trainer.user_id),
                "full_name": trainer.user.full_name,
            } if trainer else None,
            "sport": {
                "id": str(sport.id),
                "name": sport.name
            } if sport else None,
            "height": str(instance.height) if instance.height else None,
            "weight": str(instance.weight) if instance.weight else None,
            "sport_rank": instance.sport_rank,
        }

    @classmethod
    def _get_approval_fields(cls) -> list[str]:
        """
        Approval required fields for Sportsman
        """
        return ["sport", "height", "weight", "sport_rank", "trainer"]


# -- Trainer Approval Snapshot Serializers --
class TrainerSnapshotSerializer(serializers.Serializer):
    height = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    weight = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    skill_level = serializers.CharField(required=False, allow_null=True, max_length=100)
    sport = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), required=False, allow_null=True)
    federation = serializers.PrimaryKeyRelatedField(queryset=Federation.objects.all(), required=False, allow_null=True)

    def to_internal_value(self, data: dict[str, t.Any]) -> dict[str, t.Any]:
        """
        Allow deserialization from both:
        - {"sport": "uuid", "federation": "uuid", ...}
        - {"sport": {"id": "uuid", ...}, "federation": {"id": "uuid", ...}, ...}
        """
        if isinstance(data.get("sport"), dict):
            data["sport"] = data["sport"].get("id")
        if isinstance(data.get("federation"), dict):
            data["federation"] = data["federation"].get("id")
        logger.debug(f"Deserialized Internal data: {data}")
        return super().to_internal_value(data)

    def to_new_snapshot(self, validated_data: dict) -> dict:
        sport: Sport = validated_data.get("sport")
        federation: Federation = validated_data.get("federation")
        return {
            "federation": {
                "id": str(federation.id),
                "name": federation.name
            } if federation else None,
            "sport": {
                "id": str(sport.id),
                "name": sport.name
            } if sport else None,
            "height": str(validated_data.get("height")),
            "weight": str(validated_data.get("weight")),
            "skill_level": validated_data.get("skill_level"),
        }

    def to_old_snapshot(self, instance: Trainer) -> dict:
        sport: Sport = instance.sport
        federation: Federation = instance.federation
        return {
            "federation": {
                "id": str(federation.id),
                "name": federation.name
            } if federation else None,
            "sport": {
                "id": str(sport.id),
                "name": sport.name
            } if sport else None,
            "height": str(instance.height) if instance.height else None,
            "weight": str(instance.weight) if instance.weight else None,
            "skill_level": instance.skill_level,
        }

    @classmethod
    def _get_approval_fields(cls) -> list[str]:
        """
        Approval required fields for Trainer
        """
        return ["federation", "sport", "height", "weight", "skill_level"]


class FederationAdminApprovalSnapshotSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, allow_null=True, max_length=255)
    phone_number = serializers.CharField(required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_null=True)
    birth_date = serializers.DateField(required=False, allow_null=True)

    def to_new_snapshot(self, instance: User) -> dict:
        return {
            "full_name": instance.get_full_name(),
            "phone_number": instance.phone_number,
            "email": instance.email,
            "birth_date": instance.birth_date.isoformat() if instance.birth_date else None,
        }
