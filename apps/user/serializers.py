from django.contrib.auth import authenticate
from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.db.models import Sum

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

import rest_framework_simplejwt.tokens as jwt_tokens
import rest_framework_simplejwt.serializers as jwt_serializers

# custom
from .models import (
    User,
    Sportsman,
    Trainer,
    Education,
    Result,
    Media,
)

from shared.addons.custom_logging import logger
from shared.addons.exceptions import raise_validation_error
from shared.addons.utils import CorrectPath
from shared.addons.send_verification import (
    send_verification_code,
    verify_code,
    check_verification_status,
)
from datetime import date

SEND_VERIFICATION_ACTION = (
    ("signup", "signup"),
    ("login", "login"),
    ("forgot_password", "forgot_password"),
    ("change_phone_number", "change_phone_number"),
)


class SendVerificationCodeSerializer(serializers.Serializer): # noqa
    phone_number = serializers.CharField()
    action = serializers.ChoiceField(choices=SEND_VERIFICATION_ACTION)

    def validate(self, attrs):
        action = attrs.get("action")
        phone_number = attrs.get("phone_number")
        user = User.objects.filter(phone_number=phone_number).first()

        if action == "signup" and user:
            raise_validation_error(message=_("Phone number is already registered"))

        if action in ["forgot_password", "login"] and not user:
            raise_validation_error(message=_("Your phone number is not registered"))
        
        return attrs
    

class VerifyCodeSerializer(serializers.Serializer):  # noqa
    code = serializers.CharField()
    phone_number = serializers.CharField()
    action = serializers.ChoiceField(choices=SEND_VERIFICATION_ACTION, required=False)

    def get_tokens(self):  # noqa
        action = self.validated_data.get("action", None)
        phone_number = self.validated_data.get("phone_number")

        if action == "login":
            user = User.objects.filter(phone_number=phone_number).first()
            if not user:
                raise_validation_error(message=_("User not found"))
            return user.tokens()
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.validated_data.get('action') == 'login':
            data["tokens"] = self.get_tokens()
        return data


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            "name",
            "sport_type",
            "start_year",
            "end_year",
            "currently_studying",
        ]

    def validate(self, attrs):
        start_year = attrs.get("start_year")
        end_year = attrs.get("end_year")
        if start_year and end_year and start_year >= end_year:
            raise_validation_error(message=_("Start year must be less than end year"))
        
        return attrs


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = [
            "tournament_name",
            "country",
            "start_year",
            "end_year",
            "currently_participating",
            "rating",
            "logo",
        ]

    def validate(self, attrs):
        start_year = attrs.get("start_year")
        end_year = attrs.get("end_year")
        if start_year and end_year and start_year >= end_year:
            raise_validation_error(message=_("Start year must be less than end year"))
        return attrs


class MediaSerializer(serializers.ModelSerializer):
    owner = serializers.ChoiceField(
        choices=(("sportsman", "sportsman"), ("trainer", "trainer"), ("media", "media")), write_only=True
    )

    class Meta:
        model = Media
        fields = [
            "id", "media_type", "size", "extension", "created_time", "file", "owner"
        ]
        read_only_fields = ["created_time", "size", "extension", "media_type"]

    def create(self, validated_data):
        owner = validated_data.pop("owner", None)
        media_instance = Media(**validated_data)

        if owner:
            correct_path = CorrectPath('media', owner=owner)
            media_instance.file.field.upload_to = correct_path
        media_instance.save()
        return media_instance


class UsersMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "email",
            "photo",
            "birth_date",
            "is_superuser",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.user_role == "sportsman":
            data["sportsman_profile"] = SportsmanSerializer(instance.sportsman_profile).data
        elif instance.user_role == "trainer":
            data["trainer_profile"] = TrainerSerializer(instance.trainer_profile).data
        return data

class SportsmanRegisterSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True, required=True)
    results = ResultSerializer(many=True, required=True)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=True)
    moving_date_year = serializers.IntegerField(write_only=True)
    moving_date_month = serializers.IntegerField(write_only=True)

    class Meta:
        model = Sportsman
        fields = [
            "id",
            "sport_type",
            "sport_direction",
            "motto",
            "height",
            "weight",
            "gender",
            "region",
            "city",
            "street",
            "place_of_birth",
            "citizenship",
            "moving_date",
            "moving_date_year",
            "moving_date_month",
            "telegram",
            "instagram",
            "educations",
            "media_ids",
            "media",
            "results",
        ]
        extra_kwargs = {"id": {"read_only": True},}
    
    def validate(self, attrs):
        year = attrs.pop("moving_date_year", None)
        month = attrs.pop("moving_date_month", None)

        if not (1 <= month <= 12):
            raise_validation_error("Invalid month. It must be between 1 and 12.")
        
        try:
            attrs["moving_date"] = date(year, month, 1)
        except ValueError:
            raise_validation_error(message=_("Invalid year or month."))
        return attrs

    def create(self, validated_data):
        educations_data = validated_data.pop("educations")
        results_data = validated_data.pop("results")
        media_ids = validated_data.pop("media_ids")

        profile = Sportsman.objects.create(**validated_data)
        logger.info(f"Sportsman Profile created -> {profile}")
        media_objects = Media.objects.filter(id__in=media_ids)
        
        if not media_objects.exists():
            logger.info(f"No media objects")
            raise_validation_error(message=_(f"At least one media must be uploaded"))
        
        # Checking if medias are not associated with another objects
        for media in media_objects:
            if media.sportsmen.exists() and not media.sportsmen.filter(id=profile.id).exists():
                raise_validation_error(message=_(f"Media {media.id} is already associated with another sportsman."))
        
        # Link existing media to the sportsman profile
        profile.media.set(media_objects)

        for education_data in educations_data:
            Education.objects.create(sportsman_profile=profile, **education_data)
        
        for result_data in results_data:
            Result.objects.create(sportsman_profile=profile, **result_data)
        
        logger.info(f"Profile is ready")
        return profile


class SportsmanSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True)
    results = ResultSerializer(many=True)
    media = MediaSerializer(many=True)

    class Meta:
        model = Sportsman
        fields = [
            "sport_type",
            "sport_direction",
            "motto",
            "height",
            "weight",
            "gender",
            "region",
            "city",
            "street",
            "place_of_birth",
            "citizenship",
            "telegram",
            "instagram",
            "educations",
            "media",
            "results",
        ]
    

class TrainerRegisterSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True, required=True)
    results = ResultSerializer(many=True, required=True)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=True)
    moving_date_year = serializers.IntegerField(write_only=True)
    moving_date_month = serializers.IntegerField(write_only=True)

    class Meta:
        model = Trainer
        fields = [
            "sport_type",
            "sport_direction",
            "motto",
            "height",
            "weight",
            "gender",
            "region",
            "city",
            "street",
            "place_of_birth",
            "citizenship",
            "moving_date",
            "moving_date_year",
            "moving_date_month",
            "number_of_games",
            "number_of_students",
            "number_of_awards",
            "telegram",
            "instagram",
            "educations",
            "media_ids",
            "results",
        ]
    
    def validate(self, attrs):
        year = attrs.pop("moving_date_year", None)
        month = attrs.pop("moving_date_month", None)

        if not (1 <= month <= 12):
            raise_validation_error("Invalid month. It must be between 1 and 12.")
        
        try:
            attrs["moving_date"] = date(year, month, 1)
        except ValueError:
            raise_validation_error(message=_("Invalid year or month."))
        return attrs
    
    def create(self, validated_data):
        educations_data = validated_data.pop("educations")
        results_data = validated_data.pop("results")
        media_ids = validated_data.pop("media_ids")

        profile = Trainer.objects.create(**validated_data)

        # Link existing media to the trainer profile
        media_objects = Media.objects.filter(id__in=media_ids)
        
        if not media_objects.exists():
            raise_validation_error(message=_(f"At least one media must be uploaded"))

        # Check if medias are not associated with another objects
        for media in media_objects:
            if media.trainer is not None and media.trainer != profile:
                raise_validation_error(message=_(f"Media {media.id} is already associated with another trainer."))

        profile.media.set(media_objects)

        for education_data in educations_data:
            Education.objects.create(trainer_profile=profile, **education_data)
        
        for result_data in results_data:
            Result.objects.create(trainer_profile=profile, **result_data)
        
        return profile
    

class TrainerSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True)
    results = ResultSerializer(many=True)
    media = MediaSerializer(many=True)

    class Meta:
        model = Trainer
        fields = [
            "sport_type",
            "sport_direction",
            "motto",
            "height",
            "weight",
            "gender",
            "region",
            "city",
            "street",
            "place_of_birth",
            "citizenship",
            "number_of_games",
            "number_of_students",
            "number_of_awards",
            "telegram",
            "instagram",
            "educations",
            "media",
            "results",
        ]

# TRIED TO MAKE PROFILE SERIALIZER DYNAMIC BUT COULDN'T
class ProfileField(serializers.Field):
    def to_representation(self, value):
        # Use the `user_role` to determine the appropriate serializer
        if value.user_role == 'sportsman':
            return SportsmanRegisterSerializer(value.sportsman_profile).data if hasattr(value, 'sportsman_profile') else None
        elif value.user_role == 'trainer':
            return TrainerRegisterSerializer(value.trainer_profile).data if hasattr(value, 'trainer_profile') else None
        return None

    def to_internal_value(self, data):
        # Return the raw data to be handled by `create` or `update`
        return data


class RegistrationSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField()
    sportsman_profile = SportsmanRegisterSerializer(required=False)
    trainer_profile = TrainerRegisterSerializer(required=False)
    # profile = ProfileField(source='*', required=False)
    # profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "first_name",
            "middle_name",
            "last_name",
            "user_role",
            "email",
            "photo",
            "birth_date",
            "user_role",
            # "profile",
            "sportsman_profile",
            "trainer_profile",
            "is_verified",
            "created_time",
        )
        extra_kwargs = {"id": {"read_only": True}, "is_verified": {"read_only": True}, "photo": {"required": False}}

    def validate(self, attrs):
        user = User.objects.filter(phone_number=attrs["phone_number"]).first()
        if user:
            raise_validation_error(message=_("Phone number is already registered"))
        return super().validate(attrs)

    def create(self, validated_data):
        user_role = validated_data.get("user_role")
        
        logger.info(f"Full validated data -> {validated_data}")
        # logger.info(f"Sportsman profile data -> {validated_data.get("sportsman_profile")}")
        sportsman_profile_data = validated_data.pop("sportsman_profile", None)
        trainer_profile_data = validated_data.pop("trainer_profile", None)
        # profile_data = validated_data.pop("profile", None)
        # print(profile_data)

        logger.info(f"Sportsman profile popped -> {sportsman_profile_data}")
        logger.info(f"User role -> {user_role}")
        with transaction.atomic():
            user = User.objects.create(**validated_data)
            logger.info(f"User created -> {user}")
            if user_role == "sportsman" and sportsman_profile_data:
                sportsman_profile_data["user"] = user
                SportsmanRegisterSerializer().create(sportsman_profile_data)
            elif user_role == "trainer" and trainer_profile_data:
                trainer_profile_data["user"] = user
                TrainerRegisterSerializer().create(trainer_profile_data)
            
            return user
    
    def get_tokens(self, user):  # noqa
        return user.tokens()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data["user_role"] == "ordinary":
            data["tokens"] = self.get_tokens(instance)
        return data


class LogoutSerializer(serializers.Serializer):  # noqa
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        # Check if new password matches the confirmation
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")
        if new_password != confirm_password:
            raise_validation_error(message=_("New password don't match"))
        
        return attrs

    def update(self, instance, validated_data):
        # Set the new password
        new_password = validated_data["new_password"]
        instance.set_password(new_password)
        instance.save()
        return validated_data
    

class UpdatePhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15, required=True)
    password = serializers.CharField(max_length=128, required=True)
    confirm_password = serializers.CharField(max_length=128, required=True)

    def validate(self, value):
        request_context = self.context.get("request")
        user = request_context.user if request_context is not None else None

        # Check if all required fields are present in the request body
        if (
            not value.get("phone_number")
            or not value.get("password")
            or not value.get("confirm_password")
        ):
            raise_validation_error(message=_("All required fields must be present"))
        # check if phone number equals to user existing phone number
        if user.phone_number == value.get("phone_number"):
            raise_validation_error(message=_("You entered your current phone number!"))

        if User.objects.filter(phone_number=value.get("phone_number")).exists():
            raise_validation_error(message=_("Phone number is already registered"))

        # Check if the password and confirm_password fields match
        if value.get("password") != value.get("confirm_password"):
            raise_validation_error(message=_("Passwords do not match"))

        # Authenticate the user based on their password
        auth_user = authenticate(username=user.username, password=value.get("password"))
        if not auth_user:
            raise_validation_error(message=_("Invalid password"))
        return value


class CustomTokenRefreshSerializer(jwt_serializers.TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        access_token_instance = jwt_tokens.AccessToken(data["access"])
        user_id = access_token_instance["user_id"]
        user = get_object_or_404(User, id=user_id)
        update_last_login(None, user)
        return data


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "last_name",
            "first_name",
            "birth_date",
        ]


class SportsmanProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = "__all__"





