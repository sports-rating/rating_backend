import typing as t

from datetime import date
from typing import Any, Dict, List

import rest_framework_simplejwt.serializers as jwt_serializers
import rest_framework_simplejwt.tokens as jwt_tokens
from rest_framework.generics import get_object_or_404
from rest_framework import serializers

from django.apps import apps

from apps.shared.utils.enums import SportRankEnum
from apps.shared.utils.logging import logger
from apps.federation.models import Federation
from apps.education.models import School
from apps.sport.models import Sport


class ChildTournamentSnapshotSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True)


class ChildSportSnapshotSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True)


# -- Sportsman Result Approval Snapshot Serializers --
class SportsmanResultSnapshotSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    country = serializers.CharField(required=False, allow_null=True)
    year = serializers.IntegerField(required=False, allow_null=True)
    # currently_participating = serializers.BooleanField(default=False)
    rating = serializers.IntegerField(required=False, allow_null=True)
    tournament = ChildTournamentSnapshotSerializer(required=False, allow_null=True)


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
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all(), required=True)
    sport = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), required=True)

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Allow deserialization from both:
        - {"school": "uuid", "sport": "uuid"}
        - {"school": {"id": "uuid", ...}, "sport": {"id": "uuid", ...}}
        """
        if isinstance(data.get("school"), dict):
            data["school"] = data["school"].get("id")
        if isinstance(data.get("sport"), dict):
            data["sport"] = data["sport"].get("id")
        logger.debug(f"Deserialized Internal data: {data}")
        return super().to_internal_value(data)

    def to_new_snapshot(self, validated_data: dict) -> dict:
        school: School = validated_data.get("school")
        sport: Sport = validated_data.get("sport")
        return {
            "school": {
                "id": str(school.id),
                "name": school.name
            } if school else None,
            "sport": {
                "id": str(sport.id),
                "name": sport.name
            } if sport else None,
        }
