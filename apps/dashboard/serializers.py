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
    Tournament, 
    Sport
)



from shared.addons.exceptions import raise_validation_error
from shared.addons.utils import CorrectPath


class InlineMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = [
            "id",
            "media_type",
            "file",
            "size",
            "extension",
        ]


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


class SportCreateSerializer(serializers.ModelSerializer):
    logo = InlineMediaSerializer(many=True, read_only=True)
    logo_id = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)

    class Meta:
        model = Sport
        fields = (
            "id",
            "name",
            "logo_id",
            "logo",
        )
        extra_kwargs = {"id": {"read_only": True}, "logo": {"required": False}}

    def create(self, validated_data):
        sport = Sport.objects.filter(name=validated_data["name"]).first()
        sport_name = validated_data["name"]
        if sport:
            raise_validation_error(message=_(f"{sport_name} - sport is already created"))

        logo_id = validated_data.pop("logo_id", None)
        sport = Sport.objects.create(**validated_data)

        if logo_id:
            media_object = Media.objects.filter(id__in=logo_id)
            sport.logo.set(media_object)
        return sport


class SportSerializer(serializers.ModelSerializer):
    logo = InlineMediaSerializer(many=True, read_only=True)
    
    class Meta:
        model = Sport
        fields = (
            "id",
            "name",
            "logo",
        )


class TournamentCreateSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source='sport', write_only=True)
    logo_id = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    logo = InlineMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "start_time",
            "end_time",
            "place",
            "division",
            "sport_id",
            "logo_id",
            "logo",
        )
        extra_kwargs = {"id": {"read_only": True}, "logo": {"required": False}}
    
    def validate(self, attrs):
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
    
        if start_time and end_time and start_time > end_time:
            raise_validation_error(message=_("Start time must be less than end time"))  
        
        return attrs
    
    def create(self, validated_data):
        sport = validated_data.pop("sport")
        logo_id = validated_data.pop("logo_id", None)
        tournament = Tournament.objects.create(sport=sport, **validated_data)
        if logo_id:
            media_object = Media.objects.filter(id__in=logo_id)
            tournament.logo.set(media_object)
        return tournament

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_name"] = instance.sport.name
        return data


class TournamentSerializer(serializers.ModelSerializer):
    sport = SportSerializer(many=False)
    logo = InlineMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "start_time",
            "end_time",
            "place",
            "division",
            "sport",
            "logo",
        )
