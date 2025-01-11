from datetime import datetime

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
    Sport,
    Team
)


from shared.addons.custom_logging import logger
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
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.user_role == "sportsman":
            if instance.sportsman_profile and instance.sportsman_profile.trainer:
                data["trainer_id"] = instance.sportsman_profile.trainer.user.id
                data["trainer_name"] = f'{instance.sportsman_profile.trainer.user}'
        return data
    

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

    def update(self, instance, validated_data):
        logo_id = validated_data.pop("logo_id", None)
        if logo_id:
            current_logos = instance.logo.all() # Get the current logos
            instance.logo.clear() # Clear the current logo associations
            current_logos.delete() # Delete the old Media objects
            media_object = Media.objects.filter(id__in=logo_id)
            instance.logo.set(media_object)

        return super().update(instance, validated_data)

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

    def update(self, instance, validated_data):
        logo_id = validated_data.pop("logo_id", None)
        if logo_id:
            current_logos = instance.logo.all() # Get the current logos
            instance.logo.clear() # Clear the current logo associations
            current_logos.delete() # Delete the old Media objects
            media_object = Media.objects.filter(id__in=logo_id)
            instance.logo.set(media_object)

        return super().update(instance, validated_data)
    
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


class TeamCreateSerializer(serializers.ModelSerializer):
    logo = InlineMediaSerializer(many=True, read_only=True)
    logo_id = serializers.UUIDField(format='hex_verbose', write_only=True, required=False)
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source='sport', write_only=True)
    member_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=True)

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "logo",
            "logo_id",
            "sport_id",
            "founded_year",
            "member_ids",
            "social_media",
            "wins",
            "losses",
            "draws",
        )
        extra_kwargs = {"id": {"read_only": True}, "wins": {"required": False}, "losses": {"required": False}, "draws": {"required": False}}
    
    def validate(self, attrs):
        founded_year = attrs.get("founded_year", None)
        name = attrs.get("name", None)
        team = Team.objects.filter(name=name).first()
        if team:
            raise_validation_error(message=_("Team with name already created"))

        current_year = datetime.now().year
        if founded_year and founded_year > current_year:
            raise_validation_error(message=_("Founded year must be less than current year"))
        
        return attrs

    def create(self, validated_data):
        sport = validated_data.pop("sport")
        logo_id = validated_data.pop("logo_id", None)
        member_ids = validated_data.pop("member_ids")

        team = Team.objects.create(sport=sport, **validated_data)

        if logo_id:
            media_object = Media.objects.get(id=logo_id)
            team.logo.add(media_object)
        
        if member_ids:
            member_objects = User.objects.filter(id__in=member_ids)
            team.members.set(member_objects)
        
        return team
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_name"] = instance.sport.name 
        logger.info(f"Members: {instance.members}")
        data["members"] = UserListSerializer(
            [member for member in instance.members.all()],
            many=True,
        ).data
        return data
    

class TeamUpdateSerializer(TeamCreateSerializer):
    logo = InlineMediaSerializer(many=True, read_only=True)
    logo_id = serializers.UUIDField(format='hex_verbose', write_only=True, required=False)
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source='sport', write_only=True, required=False)
    member_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)

    class Meta(TeamCreateSerializer.Meta):
        extra_kwargs = {
            **TeamCreateSerializer.Meta.extra_kwargs, 
        }
    
    def update(self, instance, validated_data):
        logo_id = validated_data.pop("logo_id", None) # m-t-m
        member_ids = validated_data.pop("member_ids", None) # m-t-m

        # Update basic team fields
        for attrs, value in validated_data.items():
            setattr(instance, attrs, value)
        instance.save()

        if member_ids:
            member_objects = User.objects.filter(id__in=member_ids)
            instance.members.set(member_objects)
        
        if logo_id:
            logo_object = Media.objects.get(id=logo_id)
            instance.logo.set(logo_object)

        return instance


class TeamSerializer(serializers.ModelSerializer):
    logo = InlineMediaSerializer(many=True)
    sport = SportSerializer()
    members = UserListSerializer(many=True)

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "sport",
            "founded_year",
            "logo",
            "members",
            "social_media",
            "wins",
            "losses",
            "draws",
        ]

