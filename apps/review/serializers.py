import typing as t
import os
from datetime import datetime
from pathlib import Path

from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.db.models import Sum, Count
from django.conf import settings
from django.core.files import File
from django.contrib.contenttypes.models import ContentType

from rest_framework import serializers

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
from apps.shared.utils import enums

from apps.review.models import Comment
from apps.user.models import User
from apps.sport.models import SportInstitution


class CommentSerializer(RequestContextMixin, serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = (
            "id",
            "user",
            "sport_institution",
            "text",
            "rating",
            "created_time",
        )
        read_only_fields = ("id", "user", "created_time")

    def validate(self, attrs: t.Dict) -> t.Dict:
        user: User = self.request.user  # type: ignore
        sport_institution: SportInstitution = attrs.get("sport_institution")
        rating: int = int(attrs.get("rating"))
        logger.info(f"User: {user}")
        logger.info(f"Sport Institution: {sport_institution}")

        if not (1 <= rating <= 5):
            raise_validation_error(message=_("Rating must be between 1 and 5."))

        # # Check if the user has already commented on this sport institution
        # if Comment.objects.filter(
        #     user=user,
        #     sport_institution=sport_institution
        # ).exists():
        #     raise_validation_error(message=_("You have already commented on this sport institution."))

        return attrs

    @transaction.atomic
    def create(self, validated_data: t.Dict) -> Comment:
        user = self.request.user
        sport_institution = validated_data.pop("sport_institution")

        comment = Comment.objects.create(
            user=user,
            sport_institution=sport_institution,
            **validated_data
        )

        # Optionally, you can update the average rating of the sport institution here
        self._update_sport_institution_rating(sport_institution)
        return comment

    def _update_sport_institution_rating(self, sport_institution: SportInstitution):
        agg_result = Comment.objects.filter(
            sport_institution=sport_institution
        ).aggregate(avg_rating=Sum('rating'), count=Count('id'))

        avg_rating = agg_result['avg_rating'] or 0
        count = agg_result['count'] or 0

        sport_institution.rating = round((avg_rating / count), 1) if count > 0 else 0
        sport_institution.review_count = count
        sport_institution.save()

    def to_representation(self, instance: Comment) -> t.Dict:
        data = super().to_representation(instance)
        data['user'] = {
            "id": instance.user.id,
            "first_name": instance.user.first_name,
            "last_name": instance.user.last_name,
            "profile_picture": get_file_full_url(instance.user.profile_photo) if instance.user.profile_photo else None,
        }
        if instance.sport_institution:
            data['sport_institution'] = {
                "id": instance.sport_institution.id,
                "name": instance.sport_institution.name,
            }
        return data
