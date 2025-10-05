import decimal
import typing as t

from datetime import date

import rest_framework_simplejwt.serializers as jwt_serializers
import rest_framework_simplejwt.tokens as jwt_tokens
from rest_framework.generics import get_object_or_404
from rest_framework import serializers

from django.apps import apps

from apps.shared.utils.enums import SportRankEnum
from apps.shared.utils.logging import logger
from apps.federation.models import Federation, FederationAgeGroup
from apps.sport.models import Sport, Tournament, SportInstitution
from apps.user.models import User, Trainer, Sportsman


class ChildTournamentSnapshotSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True)


class ChildSportSnapshotSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True)


# -- Sportsman Result Approval Snapshot Serializers --
class SportsmanResultSnapshotSerializer(serializers.Serializer):
    country = serializers.CharField(required=False, allow_null=True)
    year = serializers.IntegerField(required=False, allow_null=True)
    age_group = serializers.PrimaryKeyRelatedField(queryset=FederationAgeGroup.objects.all(), required=False, allow_null=True)
    weight = serializers.CharField(required=False, allow_null=True, max_length=10)
    rating = serializers.IntegerField(required=False, allow_null=True)
    tournament = serializers.PrimaryKeyRelatedField(queryset=Tournament.objects.all(), required=True)
    score = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    # id = serializers.UUIDField(required=False, allow_null=True)
    # currently_participating = serializers.BooleanField(default=False)
    # tournament = ChildTournamentSnapshotSerializer(required=False, allow_null=True)

    def to_internal_value(self, data: dict[str, t.Any]) -> dict[str, t.Any]:
        """
        Allow deserialization from both:
        - {"tournament": "uuid", "age_group": "uuid", ...}
        - {"tournament": {"id": "uuid", ...}, "age_group": {"id": "uuid", ...}, ...}
        """
        if isinstance(data.get("age_group"), dict):
            data["age_group"] = data["age_group"].get("id")
        if isinstance(data.get("tournament"), dict):
            data["tournament"] = data["tournament"].get("id")
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
        }


# -- Sportsman Approval Snapshot Serializers --
class SportsmanSnapshotSerializer(serializers.Serializer):
    height = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    weight = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    sport_rank = serializers.ChoiceField(choices=SportRankEnum.choices(), required=False, allow_null=True)
    sport = ChildSportSnapshotSerializer(required=False, allow_null=True)


# -- Trainer Approval Snapshot Serializers --
class TrainerSnapshotSerializer(serializers.Serializer):
    height = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    weight = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    skill_level = serializers.CharField(required=False, allow_null=True, max_length=100)
    sport = ChildSportSnapshotSerializer(required=False, allow_null=True)


# -- Trainer WorkPlace Snapshot Serializers --
class TrainerWorkPlaceSnapshotSerializer(serializers.Serializer):
    sport_institution = serializers.PrimaryKeyRelatedField(queryset=SportInstitution.objects.all(), required=True)
    sport = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), required=True)

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
