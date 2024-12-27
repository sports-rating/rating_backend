from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from user.models import (
    User,
    Sportsman,
    Trainer,
    Media,
    Education,
    Result,
)

from dashboard.models import (
    Tournament
)


from shared.addons.exceptions import raise_validation_error
from shared.addons.utils import CorrectPath


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


class TournamentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "start_time",
            "end_time",
            "place",
            "division",
            "sport_type"
        )
        extra_kwargs = {"id": {"read_only": True}}
    
    def validate(self, attrs):
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
        if start_time and end_time and start_time > end_time:
            raise_validation_error(message=_("Start time must be less than end time"))  
        
        return attrs


class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "start_time",
            "end_time",
            "place",
            "division",
            "sport_type"
        )
        