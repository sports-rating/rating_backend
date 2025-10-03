import typing as t

from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.db.models import Sum, QuerySet
from django.conf import settings

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.general import (
    check_uniqueness,
    check_m2m_uniqueness
)
from apps.shared.serializers import (
    TrainerWorkPlaceSnapshotSerializer,
    EducationSnapshotSerializer
)
from apps.shared.utils import enums
from apps.shared.utils.mixins import RequestContextMixin

from apps.career.models import (
    Education,
    WorkPlace,
    Result
)
from apps.sport.models import (
    Sport,
    SportInstitution,
    Tournament
)
from apps.user.models import (
    User,
    UserRequest,
    Trainer,
    ArchivedTrainer
)
from apps.federation.models import Federation
from apps.sport.serializers import TournamentSerializer
from apps.shared.services.user_request import UserRequestService


class UserRequestSerializer(RequestContextMixin, serializers.ModelSerializer):
    """
    For response only
    """
    class Meta:
        model = UserRequest
        fields = [
            "id",
            "sender",
            "receivers",
            "request_type",
            "status",
            "message_from_sender",
            "message_from_receiver",
            "old_data",
            "new_data",
            "created_time",
        ]
        read_only_fields = ["id", "sender", "created_time"]
        extra_kwargs = {
            "status": {"required": False}
        }

    def validate(self, attrs: dict) -> dict:
        request_type = attrs.get("request_type")
        sender = t.cast(User, self.request.user)
        if request_type == "sportsman_trainer_request" and sender.user_role == "trainer":
            raise_validation_error(message=_("Trainers cannot send trainer requests!"))
        return super().validate(attrs)

    def to_representation(self, instance: UserRequest) -> dict:
        data = super().to_representation(instance)
        receiver: User = instance.receivers.first()  # type: ignore
        data["sender"] = {
            "id": instance.sender.id,
            "full_name": instance.sender.full_name,
            "user_role": instance.sender.user_role,
            "phone_number": instance.sender.phone_number,
        }
        if instance.federation:
            federation: Federation = instance.federation
            logger.info(f"Federation: {federation}")
            data["receiver"] = {
                "federation": {
                    "id": federation.id,
                    "name": federation.name,
                    "phone_number": federation.phone_number,
                    "is_national": federation.is_national,
                } if federation else None
            }
        else:
            data["receiver"] = {
                "id": receiver.id,
                "full_name": receiver.full_name,
                "user_role": receiver.user_role,
                "phone_number": receiver.phone_number,
            }
        data.pop("receivers")
        return data


class EducationSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True) # sport
    school_id = serializers.PrimaryKeyRelatedField(queryset=SportInstitution.objects.all(), source="school", write_only=True)

    class Meta:
        model = Education
        fields = [
            "id",
            "sport_id",
            "school_id",
            "start_year",
            "end_year",
            "currently_studying",
        ]
        read_only_fields = ["id",]

    def validate(self, attrs: dict) -> dict:
        start_year = attrs.get("start_year")
        end_year = attrs.get("end_year")
        if start_year and end_year and start_year >= end_year:
            raise_validation_error(message=_("Start year must be less than end year"))

        return attrs

    def create(self, validated_data: dict) -> Education:
        sport = validated_data.pop("sport")
        school = validated_data.pop("school")
        education = Education.objects.create(sport=sport, school=school, **validated_data)
        return education

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.sport:
            data["sport_id"] = instance.sport.id
            data["sport"] = instance.sport.name
        if instance.sport_institution:
            data["id"] = instance.sport_institution.id
            data["name"] = instance.sport_institution.name
        return data


class TrainerWorkPlaceSerializer(RequestContextMixin, serializers.ModelSerializer):
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)

    class Meta:
        model = WorkPlace
        fields = [
            "id",
            "sport_institution",
            "sport",
            "message",
            "created_time"
        ]
        read_only_fields = ["id", "created_time"]

    def validate(self, attrs: dict) -> dict:
        sport_institution: SportInstitution = attrs.get("sport_institution")
        sport: Sport = attrs.get("sport")
        user = self.request.user  # type: ignore

        if not sport_institution.sports.filter(id=sport.id).exists():
            raise_validation_error(message=_("This sport is not offered by the selected sport institution."))

        if UserRequest.objects.filter(
            sender=user,
            request_type=enums.UserRequestTypes.TRAINER_WORKPLACE_VERIFICATION_REQUEST.value,
            status=enums.UserRequestStatus.PENDING.value
        ).exists():
            raise_validation_error(message=_("You already have a pending workplace verification request."))

        return super().validate(attrs)

    def create(self, validated_data: dict) -> t.Union[WorkPlace, UserRequest]:
        trainer: Trainer = self.request.user.trainer_profile  # type: ignore
        message_from_sender: str | None = validated_data.pop("message", None)
        federation: Federation = trainer.federation
        receivers: QuerySet[User] = federation.users.filter(user_role="federation")

        new_snapshot: dict = TrainerWorkPlaceSnapshotSerializer().to_new_snapshot(validated_data)

        user_request: UserRequest = UserRequest.objects.create(
            sender=trainer.user,
            federation=federation,
            request_type=enums.UserRequestTypes.TRAINER_WORKPLACE_VERIFICATION_REQUEST.value,
            old_data={},
            new_data=new_snapshot,
            message_from_sender=message_from_sender
        )
        user_request.receivers.set(receivers)
        user_request.save()
        logger.info(f"WorkPlace UserRequest created: {user_request}")  # LOGGING
        return user_request

    def to_representation(self, instance: WorkPlace) -> t.Optional[dict]:
        if isinstance(instance, UserRequest):
            return UserRequestSerializer(instance).data
        data = super().to_representation(instance)
        data["sport_institution"] = {
            "id": instance.sport_institution.id,
            "name": instance.sport_institution.name,
        } if instance.sport_institution else None
        data["sport"] = {
            "id": instance.sport.id,
            "name": instance.sport.name,
        } if instance.sport else None
        processed_federation = instance.request.federation if instance.request else None
        data["processed_by"] = {
            "id": processed_federation.id if processed_federation else None,
            "name": processed_federation.name if processed_federation else None
        }
        data["processed_time"] = instance.request.processed_time if instance.request else None
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
            "score",
            "gold",
            "silver",
            "bronze",
        )
        read_only_fields = ("id", "score")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['trainer_id'] = instance.trainer.user.id if instance.trainer else None
        data['trainer_name'] = str(instance.traier.user) if instance.trainer else None

        data['archived_trainer_id'] = instance.archived_trainer.id if instance.archived_trainer else None
        data['archived_trainer_name'] = instance.archived_trainer.name if instance.archived_trainer else None
        return data


class EducationSerializer(RequestContextMixin, serializers.ModelSerializer):
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)

    class Meta:
        model = Education
        fields = [
            "id",
            "sport",
            "sport_institution",
            "trainer",
            "start_year",
            "end_year",
            "currently_studying",
            "message",
            "created_time"
        ]
        read_only_fields = ["id", "created_time"]

    def validate(self, attrs: dict) -> dict:
        sport_institution: SportInstitution = attrs.get("sport_institution")
        sport: Sport = attrs.get("sport")

        if not sport_institution.sports.filter(id=sport.id).exists():
            raise_validation_error(message=_("This sport is not offered by the selected sport institution."))

        start_year = attrs.get("start_year")
        end_year = attrs.get("end_year")
        if start_year and end_year and start_year >= end_year:
            raise_validation_error(message=_("Start year must be less than end year"))

        return super().validate(attrs)

    @transaction.atomic
    def create(self, validated_data: dict) -> t.Union[Education, UserRequest]:
        user: User = self.request.user  # type: ignore
        trainer: Trainer = validated_data.get("trainer")
        message_from_sender: str | None = validated_data.pop("message", None)

        new_snapshot: dict = EducationSnapshotSerializer().to_new_snapshot(validated_data)

        user_request, message, success = UserRequestService.create_request(
            sender=user,
            receivers=User.objects.filter(id=trainer.user_id),
            request_type=enums.UserRequestTypes.EDUCATION_VERIFICATION_REQUEST.value,
            old_data={},
            new_data=new_snapshot,
            message_from_sender=message_from_sender
        )
        if not success:
            raise_validation_error(message=message)

        logger.info(f"Education UserRequest created: {user_request}")  # LOGGING
        return user_request

    def to_representation(self, instance: Education) -> t.Optional[dict]:
        if isinstance(instance, UserRequest):
            return UserRequestSerializer(instance).data
        data = super().to_representation(instance)
        data["trainer"] = {
            "id": instance.trainer.user.id,
            "full_name": instance.trainer.user.full_name,
            "phone_number": instance.trainer.user.phone_number,
        }
        data["sport_institution"] = {
            "id": instance.sport_institution.id,
            "name": instance.sport_institution.name,
            "phone_number": instance.sport_institution.phone_number,
            "director": instance.sport_institution.director,
            "type": instance.sport_institution.type,
            "address": instance.sport_institution.address,
        } if instance.sport_institution else None
        data["sport"] = {
            "id": instance.sport.id,
            "name": instance.sport.name,
        } if instance.sport else None
        return data
