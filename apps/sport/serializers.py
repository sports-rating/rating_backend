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

from apps.sport.models import (
    Sport,
    Tournament,
    Result,
    Team,
)

from apps.user.models import (
    User,
    Trainer,
    ArchivedTrainer
)

from apps.dashboard.serializers import (
    UserListSerializer
)


class SportCreateSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField(required=False)

    class Meta:
        model = Sport
        fields = (
            "id",
            "name",
            "logo",
        )
        extra_kwargs = {"id": {"read_only": True}, "logo": {"required": False}}

    def validate(self, attrs):
        sport_name = attrs.get("name")
        if Sport.objects.filter(name=sport_name).exists():
            raise_validation_error(message=_(f"{sport_name} - sport is already created"))
        return attrs


class SportSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Sport
        fields = (
            "id",
            "name",
            "logo",
        )

    def get_logo(self, obj) -> Optional[str]:
        """Ensure full URL for the logo file"""
        request = self.context.get("request")  # Get the request context
        if obj.logo:  # Make sure the file exists
            return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url
        return None


class TournamentCreateSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True)
    logo = serializers.ImageField(required=False)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "sport_id",
            "logo",
        )
        extra_kwargs = {
            "id": {"read_only": True}, 
            "logo": {"required": False},
        }
    
    def validate(self, attrs):
        name = attrs.get("name", None)
        instance = self.instance  # This will be None during creation and the instance during updating

        if instance:  # Only for updates
            current_name = instance.name

            # Check if the name is being updated
            is_name_updated = name is not None and name != current_name

            # If name is being updated, perform the uniqueness check
            if is_name_updated:
                queryset = Tournament.objects.filter(name=name)
                queryset = queryset.exclude(id=instance.id)  # Exclude the current instance

                if queryset.exists():
                    raise_validation_error(message=_("Tournament with this name already exists!"))
        
        else:  # For creation
            if name:
                queryset = Tournament.objects.filter(name=name)
                if queryset.exists():
                    raise_validation_error(message=_("Tournament with this name already exists!"))

        return attrs
    
    def create(self, validated_data):
        sport = validated_data.pop("sport")
        tournament = Tournament.objects.create(sport=sport, **validated_data)       
        return tournament

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_name"] = instance.sport.name
        return data


class TournamentSerializer(serializers.ModelSerializer):
    sport = SportSerializer(many=False)
    logo = serializers.ImageField(required=False)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "sport",
            "logo",
        )


class ResultCreateSerializer(serializers.ModelSerializer):
    tournament_id = serializers.PrimaryKeyRelatedField(queryset=Tournament.objects.all(), source="tournament", write_only=True)
    trainer_id = serializers.PrimaryKeyRelatedField(queryset=Trainer.objects.all(), source="trainer", required=False, allow_null=True)
    archived_trainer_name = serializers.CharField(max_length=255, required=False, allow_null=True)

    class Meta:
        model = Result
        fields = [
            "id",
            "country",
            "tournament_id",
            "trainer_id",
            "archived_trainer_name",
            "year",
            "currently_participating",
            "rating",
            "additional_attributes",
            "gold",
            "silver",
            "bronze",
        ]
        extra_kwargs = {"id": {"read_only": True}, "country": {"required": False}}

    def create(self, validated_data):
        tournament = validated_data.pop('tournament')
        trainer = validated_data.pop("trainer")
        archived_trainer_name = validated_data.pop("archived_trainer_name", None)
        if trainer:
            result = Result.objects.create(trainer=trainer, tournament=tournament, **validated_data)
        elif archived_trainer_name:
            archived_trainer = ArchivedTrainer.objects.create(name=archived_trainer_name)
            result = Result.objects.create(archived_trainer=archived_trainer, tournament=tournament, **validated_data)
        else:  
            result = Result.objects.create(tournament=tournament, **validated_data)
        return result
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tournament_id"] = instance.tournament.id
        data["tournament_name"] = instance.tournament.name
        
        data["trainer_id"] = instance.trainer.user.id if instance.trainer else None
        data["trainer_name"] = str(instance.trainer.user) if instance.trainer else None
        
        data["archived_trainer_id"] = instance.archived_trainer.id if instance.archived_trainer else None
        data["archived_trainer_name"] = instance.archived_trainer.name if instance.archived_trainer else None
        return data


class ResultSerializer(serializers.ModelSerializer):
    tournament = TournamentSerializer(many=False)
    
    class Meta:
        model = Result
        fields = (
            "id",
            "country",
            "year",
            "currently_participating",
            "rating",
            "tournament",
            "additional_attributes",
            "gold",
            "silver",
            "bronze",
        )
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['trianer_id'] = instance.trainer.user.id if instance.trainer else None
        data['trainer_name'] = str(instance.traier.user) if instance.trainer else None

        data['archived_trainer_id'] = instance.archived_trainer.id if instance.archived_trainer else None
        data['archived_trainer_name'] = instance.archived_trainer.name if instance.archived_trainer else None
        return data


class TeamCreateSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField(required=False)
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source='sport', write_only=True)
    member_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=True)

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "logo",
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
        member_ids = validated_data.pop("member_ids")

        team = Team.objects.create(sport=sport, **validated_data)
        
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
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source='sport', write_only=True, required=False)
    member_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)

    class Meta(TeamCreateSerializer.Meta):
        extra_kwargs = {
            **TeamCreateSerializer.Meta.extra_kwargs, 
        }
    
    def update(self, instance, validated_data):
        member_ids = validated_data.pop("member_ids", None) # m-t-m

        # Update basic team fields
        for attrs, value in validated_data.items():
            setattr(instance, attrs, value)
        instance.save()

        if member_ids:
            member_objects = User.objects.filter(id__in=member_ids)
            instance.members.set(member_objects)

        return instance


class TeamSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField()
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
