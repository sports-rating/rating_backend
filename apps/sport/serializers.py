import typing as t
import os
from datetime import datetime
from pathlib import Path

from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings
from django.core.files import File

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.mixins import RequestContextMixin
from apps.shared.utils.general import (
    get_file_full_url,
    calculate_file_size,
    check_uniqueness,
    check_phone_valid,
    send_sport_institution_message
)

from apps.sport.models import (
    Sport,
    Tournament,
    SportInstitution,
    Team,
    ScoringPolicy,
    SportInstitutionRequest,
    SportInstitutionMedia,
    SportType
)
from apps.federation.models import (
    Federation,
)
from apps.user.models import (
    User,
    Trainer,
    ArchivedTrainer,
)
from apps.shared.models import Region, District

from apps.dashboard.serializers import (
    UserListSerializer
)
# from apps.user.tasks import recalculate_user_points_task
from apps.shared.services.scoring_service import ScoringService
from apps.shared.utils import enums
from apps.shared.serializers import BaseMediaSerializer


class SportTypeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = SportType
        fields = (
            "id",
            "name",
            "created_time"
        )
        read_only_fields = ("created_time",)
        validators = []


class SportSerializer(serializers.ModelSerializer):
    types = SportTypeSerializer(many=True, required=False)

    class Meta:
        model = Sport
        fields = (
            "id",
            "name",
            "logo",
            "types",
            "created_time"
        )
        read_only_fields = ("id", "created_time")
        extra_kwargs = {"logo": {"required": False}}

    def validate(self, attrs: dict) -> dict:
        instance: Sport = self.instance
        check_uniqueness("name", attrs, Sport, instance)
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        sport_types = validated_data.pop("types", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # CUD(Create, Update, Delete) pattern is being used here
        if sport_types:
            left_sport_types_id = []

            for sport_type in sport_types:
                sport_type_id = sport_type.get("id", None)
                name = sport_type.get("name")
                if sport_type_id:  # if id exists, update the existing sport type
                    SportType.objects.filter(id=sport_type_id).update(**sport_type)
                    left_sport_types_id.append(sport_type_id)
                else:  # if id does not exist, create a new sport type
                    # Check if the same sport/type already exists
                    existing = SportType.objects.filter(
                        sport=instance,
                        name=sport_type.get("name")
                    ).first()
                    if existing:
                        raise_validation_error(message=_(f"Sport Type with name '{name}' already exists for this sport."))
                    new_sport_type = SportType.objects.create(sport=instance, **sport_type)
                    left_sport_types_id.append(new_sport_type.id)

            # Delete sport types that are no longer present
            SportType.objects.filter(sport=instance).exclude(id__in=left_sport_types_id).delete()
        return instance

    def to_representation(self, instance: Sport) -> dict:
        data: dict = super().to_representation(instance)
        data["logo"] = get_file_full_url(instance.logo.url) if instance.logo else None
        return data


class SportInstitutionMediaSerializer(BaseMediaSerializer):
    class Meta:
        model = SportInstitutionMedia
        fields = [
            "id",
            "sport_institution",
            "media_type",
            "size",
            "extension",
            "file",
            "created_time"
        ]
        read_only_fields = ["id", "size", "extension", "media_type", "created_time"]

    def validate(self, data) -> dict:
        return super().validate(data)


class SportInstitutionSerializer(serializers.ModelSerializer):
    media = SportInstitutionMediaSerializer(many=True, read_only=True)

    class Meta:
        model = SportInstitution
        fields = [
            "id",
            "name",
            "phone_number",
            "director",
            "type",
            "work_time",
            "address",
            "latitude",
            "longitude",
            "region",
            "district",
            "sports",
            "media",
            "rating",
            "review_count",
            "created_time",
        ]
        read_only_fields = [
            "id",
            "rating",
            "review_count",
            "created_time"
        ]

    def validate(self, attrs: dict) -> dict:
        instance = getattr(self, 'instance', None)

        check_uniqueness("name", attrs, SportInstitution, instance)
        check_uniqueness("phone_number", attrs, SportInstitution, instance)

        return attrs

    def create(self, validated_data: dict) -> SportInstitution:
        sports: list[Sport] = validated_data.pop("sports", None)

        with transaction.atomic():
            sport_institution = SportInstitution.objects.create(**validated_data)

            if sports:
                sport_institution.sports.set(sports)

        return sport_institution

    def update(self, instance: SportInstitution, validated_data: dict) -> SportInstitution:
        sports: list[Sport] = validated_data.pop("sports", [])

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if sports:
                instance.sports.set(sports)

        return instance

    def to_representation(self, instance: SportInstitution) -> dict:
        data =  super().to_representation(instance)
        data["user"] = {
            "id": instance.user.id,
            "full_name": instance.user.full_name,
            "phone_number": instance.user.phone_number,
        } if instance.user else None
        data["region"] = {
            "id": instance.region.id,
            "name": instance.region.name
        } if instance.region else None
        data["district"] = {
            "id": instance.district.id,
            "name": instance.district.name
        } if instance.district else None
        data["sports"] = SportSerializer(
            instance.sports.all(),
            many=True
        ).data
        data["trainers"] = [
            {
                "id": work_place.trainer.user_id,
                "full_name": work_place.trainer.user.full_name,
                "phone_number": work_place.trainer.user.phone_number,
            }
            for work_place in instance.institution_trainer_work_places.select_related("trainer").distinct('trainer').all()
        ]
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
            raise_validation_error(message=_("Team with this name already exists"))

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


class SportInstitutionRequestSerializer(RequestContextMixin, serializers.ModelSerializer):
    class Meta:
        model = SportInstitutionRequest
        fields = [
            "id",
            "manager_first_name",
            "manager_last_name",
            "manager_phone_number",
            "school_name",
            "school_phone_number",
            "school_director",
            "school_type",
            "school_address",
            "school_latitude",
            "school_longitude",
            "school_region",
            "school_district",
            "school_sports",
            "processed_by",
            "processed_time",
            "additional_info",
            "status",
            "created_time",
        ]
        read_only_fields = [
            "id",
            "created_time",
        ]

    def validate(self, attrs: dict) -> dict:
        phone_number: str = attrs.get("manager_phone_number")
        if User.objects.filter(phone_number=phone_number).exists():
            logger.error(f"Sport Institution Request: creation | User with phone number {phone_number} already exists.")
            raise_validation_error(message=_(f"User with phone number {phone_number} already exists."))

        school_phone_number: str = attrs.get("school_phone_number")

        instance = getattr(self, 'instance', None)
        attrs["name"] = attrs.get("school_name", None)
        check_uniqueness("name", attrs, SportInstitution, instance)
        attrs.pop("name", None)  # remove temporary field

        check_phone_valid(phone_number)
        check_phone_valid(school_phone_number)
        return attrs

    def create(self, validated_data: dict) -> SportInstitutionRequest:
        request = SportInstitutionRequest.objects.create(**validated_data)
        return request

    @transaction.atomic
    def update(self, instance: SportInstitutionRequest, validated_data: dict) -> SportInstitutionRequest:
        status = validated_data.get("status", None)
        processed_by = self.request.user

        if status in [enums.SportInstitutionRequestStatus.APPROVED.value, enums.SportInstitutionRequestStatus.REJECTED.value]:
            if not processed_by:
                raise_validation_error(message=_("Processed by must be set when approving or rejecting a request."))
            instance.processed_by = processed_by
            instance.processed_time = timezone.now()
            instance.status = status

        additional_info = validated_data.get("additional_info", None)
        if additional_info:
            instance.additional_info = additional_info

        instance.save()

        if status == enums.SportInstitutionRequestStatus.APPROVED.value:
            # Create SportInstitution
            sport_institution = self._create_sport_institution(instance)
            # Create SportInstitution Admin user
            admin_user = self._create_sport_institution_admin(instance, sport_institution)

            sport_institution.user = admin_user
            sport_institution.save()

        # Send SMS to the manager with login details
        status_code = send_sport_institution_message(instance.school_name, instance.manager_phone_number, status)
        if status_code != 200:
            logger.error(f"Failed to send SMS to {instance.manager_phone_number} for Sport Institution '{instance.school_name}'. Status code: {status_code}")
            raise_validation_error(message=_("Failed to send SMS notification. Please try again later."))

        return instance

    def _create_sport_institution(self, request: SportInstitutionRequest) -> SportInstitution:
        sport_institution = SportInstitution.objects.create(
            name=request.school_name,
            phone_number=request.school_phone_number,
            director=request.school_director,
            type=request.school_type,
            address=request.school_address,
            latitude=request.school_latitude,
            longitude=request.school_longitude,
            region_id=request.school_region,
            district_id=request.school_district,
        )
        if request.school_sports:
            sports = Sport.objects.filter(id__in=request.school_sports)
            sport_institution.sports.set(sports)

        # Assign default media
        default_path = os.path.join(settings.STATICFILES_DIRS[0], 'default_institution_image.png')
        with open(default_path, 'rb') as f:
            sport_institution_media = SportInstitutionMedia(
                sport_institution=sport_institution,
            )
            sport_institution_media.file.save('default_institution_image.png', File(f), save=True)

        return sport_institution

    def _create_sport_institution_admin(self, request: SportInstitutionRequest, sport_institution: SportInstitution) -> User:
        phone_number = request.manager_phone_number

        if User.objects.filter(phone_number=phone_number).exists():
            logger.error(f"Sport Institution Request: approved | User with phone number {phone_number} already exists.")
            raise_validation_error(message=_(f"User with phone number {phone_number} already exists."))

        user = User(
            first_name=request.manager_first_name,
            last_name=request.manager_last_name,
            phone_number=request.manager_phone_number,
            user_role=enums.UserRoles.SPORT_INSTITUTION_ADMIN.value,
            is_active=True,
        )
        user.save()

        return user

    def to_representation(self, instance: SportInstitutionRequest) -> dict:
        data = super().to_representation(instance)
        region = Region.objects.filter(id=instance.school_region).first()
        district = District.objects.filter(id=instance.school_district).first()
        sports = Sport.objects.filter(id__in=instance.school_sports).all()
        data["school_region"] = {
            "id": region.id,
            "name": region.name
        } if region else None
        data["school_district"] = {
            "id": district.id,
            "name": district.name
        } if district else None
        data["school_sports"] = SportSerializer(sports, many=True).data
        data["processed_by"] = {
            "id": instance.processed_by.id,
            "full_name": instance.processed_by.full_name,
            "phone_number": instance.processed_by.phone_number,
        } if instance.processed_by else None
        return data


class SportInstitutionUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "birth_date",
            "region",
            "district",
            "gender",
            "user_role",
            "created_time"
        ]
        read_only_fields = ["id", "created_time"]

    def to_representation(self, instance: User) -> dict:
        data = super().to_representation(instance)
        sport: Sport | None = self._get_sport(instance)
        trainer: User | None = self._get_trainer(instance)
        data["full_name"] = instance.full_name
        data["region"] = {
            "id": instance.region.id,
            "name": instance.region.name
        } if instance.region else None
        data["district"] = {
            "id": instance.district.id,
            "name": instance.district.name
        } if instance.district else None
        data["sport"] = {
            "id": sport.id,
            "name": sport.name,
            "logo": get_file_full_url(sport.logo.url) if sport.logo else None
        } if sport else None
        if instance.user_role == enums.UserRoles.SPORTSMAN.value:
            data["trainer"] = {
                "id": trainer.id,
                "full_name": trainer.full_name,
                "user_role": trainer.user_role,
                "phone_number": trainer.phone_number,
            } if trainer else None
        else:
            data["federation"] = {
                "id": instance.trainer_profile.federation.id,
                "name": instance.trainer_profile.federation.name
            }
        return data

    def _get_sport(self, instance: User) -> t.Union[Sport, None]:
        if instance.user_role == "sportsman":
            return instance.sportsman_profile.sport
        elif instance.user_role == "trainer":
            return instance.trainer_profile.sport
        return None

    def _get_trainer(self, instance: User) -> t.Union[User, None]:
        if instance.user_role == "sportsman":
            return instance.sportsman_profile.trainer.user
        return None
