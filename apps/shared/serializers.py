import typing as t

from datetime import date
from typing import Any, Dict, List

import rest_framework_simplejwt.serializers as jwt_serializers
import rest_framework_simplejwt.tokens as jwt_tokens
from rest_framework.generics import get_object_or_404
from rest_framework import serializers
from apps.shared.utils.enums import SportRankEnum

class ChildTournamentSnapshotSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True)

class ResultSnapshotSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    country = serializers.CharField(required=False, allow_null=True)
    year = serializers.IntegerField(required=False, allow_null=True)
    currently_participating = serializers.BooleanField(required=False, allow_null=True)
    rating = serializers.IntegerField(required=False, allow_null=True)
    tournament = ChildTournamentSnapshotSerializer(required=False, allow_null=True)


# class SportsmanSnapshotSerializer(serializers.Serializer):
#     id = serializers.UUIDField(required=False, allow_null=True)
#     height = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
#     weight = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
#     sport_rank = serializers.ChoiceField(choices=SportRankEnum.choices(), required=False, allow_null=True)
#     sport =
