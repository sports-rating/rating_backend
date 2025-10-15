from datetime import datetime

from django.utils.translation import gettext as _
from django.db import transaction

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from apps.user.models import (
    User,
    Sportsman,
    Trainer,
    UserRequest
)

from apps.dashboard.models import PrivacyPolicy, TermsOfCondition
from apps.federation.models import Federation
from apps.sport.models import Sport, SportInstitution
from apps.payment.models import Transaction

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.utils import CorrectPath
from apps.shared.utils import enums


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
            if getattr(instance, "sportsman_profile", None):
                data["sport"] = instance.sportsman_profile.sport.name if instance.sportsman_profile.sport else None
                if instance.sportsman_profile.trainer:
                    data["trainer_id"] = instance.sportsman_profile.trainer.user_id
                    data["trainer_name"] = f'{instance.sportsman_profile.trainer.user}'
        if instance.user_role == "trainer":
            if getattr(instance, "trainer_profile", None):
                data["sport"] = instance.trainer_profile.sport.name if instance.trainer_profile.sport else None
        return data


class AddUserSerializer(serializers.ModelSerializer):
    """
    User Serializer
    """
    federation = serializers.PrimaryKeyRelatedField(
        queryset=Federation.objects.all(),
        required=True,
        write_only=True
    )

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'middle_name',
            "username",
            'gender',
            'phone_number',
            'email',
            'birth_date',
            'user_role',
            'federation',
            'is_verified',
            'created_time',
        ]
        extra_kwargs: dict[str, dict] = {
            'email': {'required': False},
        }
        read_only_fields: list[str] = ['id', 'username', 'is_verified', 'created_time']

    def validate(self, attrs: dict) -> dict:
        user_role = attrs.get('user_role')
        phone_number = attrs.get('phone_number')
        email = attrs.get('email')
        if User.objects.filter(phone_number=phone_number).exists():
            raise_validation_error(message=_("User with this phone number already exists."))
        if email and User.objects.filter(email=email).exists():
            raise_validation_error(message=_("User with this email already exists."))
        if user_role not in [enums.UserRoles.ADMIN.value, enums.UserRoles.FEDERATION.value]:
            raise_validation_error(message=_("Wrong user role has been provided."))
        return attrs

    def create(self, validated_data: dict) -> User:
        federation: Federation = validated_data.pop('federation')
        user_role: str = validated_data.get('user_role')
        user = User(
            first_name=validated_data.get('first_name'),
            last_name=validated_data.get('last_name'),
            middle_name=validated_data.get('middle_name'),
            gender=validated_data.get('gender'),
            phone_number=validated_data.get('phone_number'),
            email=validated_data.get('email'),
            birth_date=validated_data.get('birth_date'),
            user_role=validated_data.get('user_role'),
            is_verified=True,
        )
        user.save()
        if user_role == enums.UserRoles.FEDERATION.value:
            # Assign user to federation
            federation.users.add(user)
            federation.save()
        return user

    def to_representation(self, instance: User) -> dict:
        data = super().to_representation(instance)
        data['federation'] = {
            'id': instance.federation.id,
            'name': instance.federation.name
        } if instance.federation else None
        return data


class SportsmanExportSerializer(serializers.ModelSerializer):
    height = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    street = serializers.SerializerMethodField()
    citizenship = serializers.SerializerMethodField()

    class Meta:
        model = Sportsman
        fields = [
            "height",
            "weight",
            "region",
            "city",
            "street",
            "citizenship",
        ]

    def get_height(self, obj):
        return obj.user_metrics.get("height") if obj.user_metrics else None

    def get_weight(self, obj):
        return obj.user_metrics.get("weight") if obj.user_metrics else None

    def get_region(self, obj):
        return obj.address.get("region") if obj.address else None

    def get_city(self, obj):
        return obj.address.get("city") if obj.address else None

    def get_street(self, obj):
        return obj.address.get("street") if obj.address else None

    def get_citizenship(self, obj):
        return obj.address.get("citizenship") if obj.address else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.trainer:
            data["trainer_name"] = f'{instance.trainer.user}'
        if instance.sport:
            data["sport"] = instance.sport.name
        return data


class TrainerExportSerializer(serializers.ModelSerializer):
    height = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    street = serializers.SerializerMethodField()
    citizenship = serializers.SerializerMethodField()

    class Meta:
        model = Sportsman
        fields = [
            "height",
            "weight",
            "region",
            "city",
            "street",
            "citizenship",
        ]

    def get_height(self, obj):
        return obj.user_metrics.get("height") if obj.user_metrics else None

    def get_weight(self, obj):
        return obj.user_metrics.get("weight") if obj.user_metrics else None

    def get_region(self, obj):
        return obj.address.get("region") if obj.address else None

    def get_city(self, obj):
        return obj.address.get("city") if obj.address else None

    def get_street(self, obj):
        return obj.address.get("street") if obj.address else None

    def get_citizenship(self, obj):
        return obj.address.get("citizenship") if obj.address else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.sport:
            data["sport"] = instance.sport.name
        return data


class UserExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "email",
            "user_role",
            "birth_date",
            "created_time",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.user_role == "sportsman":
            sportsman_data = SportsmanExportSerializer(instance.sportsman_profile).data
            data.update(sportsman_data)  # Merge sportsman data into the main data

        elif instance.user_role == "trainer":
            trainer_data = TrainerExportSerializer(instance.trainer_profile).data
            data.update(trainer_data)  # Merge trainer data into the main data

        return data


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = ("id", "title", "language", "text")

    def validate(self, attrs):
        language = attrs.get('language')
        instance = self.instance

        if instance:
            current_language = instance.language
            is_language_updated = language is not None and language != current_language

            if is_language_updated:
                queryset = PrivacyPolicy.objects.filter(language=language)
                queryset = queryset.exclude(id=instance.id)

                if queryset.exists():
                    raise_validation_error(_("Privacy Policy with this language already exists"))
        else:
            if language:
                if PrivacyPolicy.objects.filter(language=language).exists():
                    raise_validation_error(message=_("Privacy Policy with this language already exists"))

        return attrs


class TermsOfConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsOfCondition
        fields = ("id", "title", "language", "text")

    def validate(self, attrs):
        language = attrs.get("language")
        instance = self.instance

        if instance:
            current_language = instance.language
            is_language_updated = language is not None and language != current_language

            if is_language_updated:
                queryset = TermsOfCondition.objects.filter(language=language)
                queryset.exclude(id=instance.id)

                if queryset.exists():
                    raise_validation_error(_("Terms of Conditions with language already exists"))
        else:
            if language:
                if TermsOfCondition.objects.filter(language=language).exists():
                    raise_validation_error(message=_("Terms of Conditions with this language already exists"))

        return attrs


class UsersCountSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_sportsmen = serializers.IntegerField()
    total_trainers = serializers.IntegerField()
    total_sport_institution_admins = serializers.IntegerField()
    total_federation_admins = serializers.IntegerField()
    total_admins = serializers.IntegerField()

    def to_representation(self, instance) -> dict:
        users_count = User.stats.get_total_users()
        data = {
            "total_users": users_count['total_users'],
            "total_sportsmen": users_count['total_sportsmen'],
            "total_trainers": users_count['total_trainers'],
            "total_sport_institution_admins": users_count['total_sport_institution_admins'],
            "total_federation_admins": users_count['total_federation_admins'],
            "total_admins": users_count['total_admins'],
        }
        return data


class GeneralCountSerializer(serializers.Serializer):
    users = UsersCountSerializer()
    total_federations = serializers.IntegerField()
    total_sport_institutions = serializers.IntegerField()
    total_sports = serializers.IntegerField()
    total_pending_requests = serializers.IntegerField()
    total_monthly_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)

    def to_representation(self, instance) -> dict:
        data = {
            "users": UsersCountSerializer(instance={}).data,
            "total_federations": Federation.stats.get_total_federations(),
            "total_sport_institutions": SportInstitution.stats.get_total_sport_institutions(),
            "total_sports": Sport.stats.get_total_sports(),
            "total_pending_requests": self.get_total_pending_requests(),
            "total_monthly_revenue": Transaction.stats.get_monthly_revenue(),
        }
        return data

    def get_total_pending_requests(self) -> int:
        return UserRequest.objects.filter(status=enums.UserRequestStatus.PENDING.value).count()


class MainStatsSerializer(serializers.Serializer):
    general_counts = GeneralCountSerializer()
    revenue_stats = serializers.ListField()
    user_growth_stats = serializers.ListField()

    def to_representation(self, instance) -> dict:
        data = {
            "general_counts": GeneralCountSerializer(instance={}).data,
            "revenue_stats": Transaction.stats.get_last_6_months_revenue(),
            "user_growth_stats": User.stats.get_last_6_months_user_growth()
        }
        return data


class PaymentStatsSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions = serializers.IntegerField()
    total_revenue_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions_month = serializers.IntegerField()
    yearly_revenue = serializers.ListField()
    by_user_role = serializers.DictField()
    by_payment_method = serializers.DictField()

    def to_representation(self, instance) -> dict:
        data = Transaction.stats.get_detailed_statistics()
        data["total_revenue"] = float(data["total_revenue"])
        data["total_transactions"] = int(data["total_transactions"])
        data["total_revenue_month"] = float(data["total_revenue_month"])
        data["total_transactions_month"] = int(data["total_transactions_month"])
        data["yearly_revenue"] = [
            {
                "month": item["month"],
                "total_revenue": float(item["total_revenue"])
            }
            for item in data["yearly_revenue"]
        ]
        return data


class RequestStatusStatsSerializer(serializers.Serializer):
    pending = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    total = serializers.IntegerField()


class RequestStatsSerializer(serializers.Serializer):
    sportsman_trainer_request = RequestStatusStatsSerializer()
    trainer_federation_request = RequestStatusStatsSerializer()
    result_verification_request = RequestStatusStatsSerializer()
    workplace_verification_request = RequestStatusStatsSerializer()

    def to_representation(self, instance) -> dict:
        data = UserRequest.stats.get_request_statistics()
        return {
            "sportsman_trainer_request": data.get(enums.UserRequestTypes.SPORTSMAN_TRAINER_REQUEST.value, {}),
            "trainer_federation_request": data.get(enums.UserRequestTypes.TRAINER_FEDERATION_REQUEST.value, {}),
            "result_verification_request": data.get(enums.UserRequestTypes.SPORTSMAN_RESULT_VERIFICATION_REQUEST.value, {}),
            "workplace_verification_request": data.get(enums.UserRequestTypes.TRAINER_WORKPLACE_VERIFICATION_REQUEST.value, {}),
        }
