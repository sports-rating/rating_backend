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
)
from apps.shared.utils import enums
from apps.shared.utils.mixins import RequestContextMixin

from apps.career.models import (
    Education,
    WorkPlace
)
from apps.sport.models import (
    Sport,
    School
)
from apps.user.models import (
    User,
    UserRequest,
    Trainer
)
from apps.federation.models import Federation
from apps.user.serializers import UserRequestSerializer


class EducationSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True) # sport
    school_id = serializers.PrimaryKeyRelatedField(queryset=School.objects.all(), source="school", write_only=True)

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
        if instance.school:
            data["school_id"] = instance.school.id
            data["school_name"] = instance.school.name
        return data


class TrainerWorkPlaceSerializer(RequestContextMixin, serializers.ModelSerializer):
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)

    class Meta:
        model = WorkPlace
        fields = [
            "id",
            "school",
            "sport",
            "message",
            "created_time"
        ]
        read_only_fields = ["id", "created_time"]

    def validate(self, attrs: dict) -> dict:
        school: School = attrs.get("school")
        sport: Sport = attrs.get("sport")
        user = self.request.user  # type: ignore

        if not school.sports.filter(id=sport.id).exists():
            raise_validation_error(message=_("This sport is not offered by the selected school."))

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
        logger.info(f"UserRequest created: {user_request}")  # LOGGING
        return user_request

    def to_representation(self, instance: WorkPlace) -> t.Optional[dict]:
        if isinstance(instance, UserRequest):
            return UserRequestSerializer(instance).data
        data = super().to_representation(instance)
        data["school"] = {
            "id": instance.school.id,
            "name": instance.school.name,
        } if instance.school else None
        data["sport"] = {
            "id": instance.sport.id,
            "name": instance.sport.name,
        } if instance.sport else None
        processed_federation = instance.request.federation if instance.request else None
        data["processed_by"] = {
            "id": processed_federation.id if processed_federation else None,
            "name": processed_federation.name if processed_federation else None
        }
        return data
