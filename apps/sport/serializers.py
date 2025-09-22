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
from apps.shared.utils.general import (
    get_file_full_url,
    calculate_file_size,
    check_uniqueness,
)

from apps.sport.models import (
    Sport,
    Tournament,
    Result,
    Team,
    ScoringPolicy,
)
from apps.federation.models import (
    Federation,
)

from apps.user.models import (
    User,
    Trainer,
    ArchivedTrainer
)

from apps.dashboard.serializers import (
    UserListSerializer
)
# from apps.user.tasks import recalculate_user_points_task
from apps.shared.services.scoring_service import ScoringService


class SportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = (
            "id",
            "name",
            "logo",
            "created_time"
        )
        read_only_fields = ("id", "created_time")
        extra_kwargs = {"logo": {"required": False}}

    def validate(self, attrs):
        sport_name = attrs.get("name")
        if Sport.objects.filter(name=sport_name).exists():
            raise_validation_error(message=_(f"{sport_name} - sport is already created"))
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["logo"] = get_file_full_url(instance.logo.url) if instance.logo else None
        return data


class ScoringPolicySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = ScoringPolicy
        fields = (
            "id",
            "position",
            "score"
        )
        validators = []


class TournamentSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True)
    logo = serializers.ImageField(required=False)
    scoring_policies = ScoringPolicySerializer(many=True, required=True)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "sport_id",
            "federation",
            "logo",
            "scoring_policies",
            "created_time"
        )
        read_only_fields = ("id", "created_time")
        extra_kwargs = {
            "logo": {"required": False},
        }

    def validate(self, attrs):
        instance = self.instance
        name = attrs.get("name", None)
        federation = attrs.get("federation", None)
        sport = attrs.get("sport", None)

        if sport and federation:
            if not federation.sports.filter(pk=sport.pk).exists():
                raise_validation_error(message=_("Selected sport does not belong to the given federation!"))
        else:
            raise_validation_error(message=_("Federation and sport must be provided."))

        if name and Tournament.objects.exclude(pk=getattr(instance, 'pk', None)).filter(name=name, sport=sport, federation=federation).exists():
            raise_validation_error(message=_("Tournament with this name already exists for the selected sport and federation!"))

        return attrs

    def create(self, validated_data):
        scoring_policies = validated_data.pop("scoring_policies", [])
        with transaction.atomic():
            tournament = Tournament.objects.create(**validated_data)
            for scoring_policy in scoring_policies:
                ScoringPolicy.objects.create(tournament=tournament, **scoring_policy)
        return tournament

    def update(self, instance, validated_data):
        scoring_policies = validated_data.pop("scoring_policies", [])
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # CUD(Create, Update, Delete) pattern is being used here
            if scoring_policies:
                left_scoring_policies_id = []

                for scoring_policy in scoring_policies:
                    scoring_policy_id = scoring_policy.get("id", None)
                    position = scoring_policy.get("position")
                    if scoring_policy_id:  # if id exists, update the existing scoring policy
                        ScoringPolicy.objects.filter(id=scoring_policy_id).update(**scoring_policy)
                        left_scoring_policies_id.append(scoring_policy_id)
                    else:  # if id does not exist, create a new scoring policy
                        # Check if the same tournament/position already exists
                        existing = ScoringPolicy.objects.filter(
                            tournament=instance,
                            position=position
                        ).first()
                        if existing:
                            raise_validation_error(message=_(f"Score for position {position} already exists for this tournament."))
                        new_scoring_policy = ScoringPolicy.objects.create(tournament=instance, **scoring_policy)
                        left_scoring_policies_id.append(new_scoring_policy.id)

                # Delete scoring policies that are no longer present
                ScoringPolicy.objects.filter(tournament=instance).exclude(id__in=left_scoring_policies_id).delete()

        # Recalculate user points after scoring policy changes
        ScoringService.recalculate_points_for_tournament(instance.id)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport"] = {
            "id": instance.sport.id,
            "name": instance.sport.name,
            "logo": get_file_full_url(instance.sport.logo.url) if instance.sport.logo else None
        } if instance.sport else None
        data["logo"] = get_file_full_url(instance.logo.url) if instance.logo else None
        data["federation"] = {
            "id": instance.federation.id,
            "name": instance.federation.name,
            "logo": get_file_full_url(instance.federation.logo.url) if instance.federation.logo else None
        } if instance.federation else None
        data['scoring_policies'] = ScoringPolicySerializer(
            instance.scoring_policies,
            many=True
        ).data
        return data


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
            "score",
            "gold",
            "silver",
            "bronze",
        ]
        read_only_fields = ("id", "score")
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
