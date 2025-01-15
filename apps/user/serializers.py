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
    School
)

from dashboard.models import (
    Tournament,
    Sport
)

from dashboard.serializers import (
    TournamentSerializer,
    SportSerializer,
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


class EducationCreateSerializer(serializers.ModelSerializer):
    sport_type = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source='sport', write_only=True)
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all(), write_only=True)

    class Meta:
        model = Education
        fields = [
            "id",
            "name",
            "sport_type",
            "school",
            "start_year",
            "end_year",
            "currently_studying",
        ]
        extra_kwargs = {"id": {"read_only": True},}

    def validate(self, attrs):
        start_year = attrs.get("start_year")
        end_year = attrs.get("end_year")
        if start_year and end_year and start_year >= end_year:
            raise_validation_error(message=_("Start year must be less than end year"))
        
        return attrs

    def create(self, validated_data):
        sport = validated_data.pop("sport")
        school = validated_data.pop("school")
        education = Education.objects.create(sport=sport, school=school, **validated_data)
        return education
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_type"] = instance.sport.name
        if instance.school:
            data["school_id"] = instance.school.id
            data["school_name"] = instance.school.name
        return data


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = (
            "id",
            "name",
            "start_year",
            "end_year",
            "currently_studying",
        )
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_type"] = instance.sport.name
        return data


class ResultCreateSerializer(serializers.ModelSerializer):
    # This field will accept the tournament ID in the request data and convert it to a Tournament object.
    # source='tournament' to map the tournament_id field to the tournament field on the Result model.
    tournament_id = serializers.PrimaryKeyRelatedField(queryset=Tournament.objects.all(), source='tournament', write_only=True)

    class Meta:
        model = Result
        fields = [
            "id",
            "country",
            "tournament_id",
            "year",
            "currently_participating",
            "rating",
            "additional_attributes",
            "number_of_gold",
            "number_of_silver",
            "number_of_bronze",
        ]
        extra_kwargs = {"id": {"read_only": True}}

    def create(self, validated_data):
        tournament = validated_data.pop('tournament')
        result = Result.objects.create(tournament=tournament, **validated_data)
        return result
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tournament_id"] = instance.tournament.id
        data["tournament_name"] = instance.tournament.name
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
            "number_of_gold",
            "number_of_silver",
            "number_of_bronze",
        )


class MediaSerializer(serializers.ModelSerializer):
    owner = serializers.ChoiceField(
        choices=(
            ("sportsman", "sportsman"), 
            ("trainer", "trainer"), 
            ("media", "media"), 
            ("user", "user"), 
            ("sport", "sport"), 
            ("tournament", "tournament"),
            ("team", "team"),
            ("school", "school"),
            ), 
            write_only=True
    )

    class Meta:
        model = Media
        fields = (
            "id", 
            "media_type", 
            "size", 
            "extension", 
            "created_time", 
            "file", 
            "owner"
        )
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
    photo = MediaSerializer(many=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "pinfl",
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


class SportsmanListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "user_role",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.sportsman_profile.sport:
            data["sport"] = instance.sportsman_profile.sport.name
        if instance.sportsman_profile.trainer:
            data["trainer_id"] = instance.sportsman_profile.trainer.user.id
            data["trainer_name"] = f'{instance.sportsman_profile.trainer.user}'
        return data

class SportsmanRegisterSerializer(serializers.ModelSerializer):
    educations = EducationCreateSerializer(many=True, required=True)
    results = ResultCreateSerializer(many=True, required=True)
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True)
    trainer_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source="trainer", write_only=True, required=False)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    moving_date_year = serializers.IntegerField(write_only=True)
    moving_date_month = serializers.IntegerField(write_only=True)
    media = MediaSerializer(many=True, required=False)

    class Meta:
        model = Sportsman
        fields = [
            "id",
            "sport_id",
            "trainer_id",
            "sport_type",
            "about_me",
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
        
        if year and month:
            if not (1 <= month <= 12):
                raise_validation_error("Invalid month. It must be between 1 and 12.")
            
            try:
                attrs["moving_date"] = date(year, month, 1)
            except ValueError:
                raise_validation_error(message=_("Invalid year or month."))
        return attrs

    def create(self, validated_data):
        educations_data = validated_data.pop("educations", None)
        results_data = validated_data.pop("results", None)
        media_ids = validated_data.pop("media_ids", None)
        sport = validated_data.pop("sport", None)
        trainer = validated_data.pop("trainer", None)
        trainer_profile = trainer.trainer_profile
        logger.info(f"Trainer profile: {trainer_profile}")
        # profile = Sportsman.objects.create(sport=sport, **validated_data)
        if trainer_profile.sport.id == sport.id:
            profile = Sportsman.objects.create(sport=sport, trainer=trainer_profile, **validated_data)
        else:
            raise_validation_error(message=_(f"Trainer's sport must be equal to sportsman's sport"))
        logger.info(f"Sportsman Profile created -> {profile}")
        
        if media_ids:
            media_objects = Media.objects.filter(id__in=media_ids)
            
            if not media_objects.exists():
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
        
        return profile
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_name"] = instance.sport.name
        if instance.trainer:
            data["trainer_id"] = User.objects.get(trainer_profile__id=instance.trainer.id).id
            data["trainer_name"] = f'{instance.trainer.user}'
        data["moving_date_month"] = str(instance.moving_date.month).zfill(2)
        data["moving_date_year"] = str(instance.moving_date.year)
        data.pop("moving_date", None)
        return data


class SportsmanUpdateSerializer(SportsmanRegisterSerializer):
    educations = EducationCreateSerializer(many=True, required=False)
    results = ResultCreateSerializer(many=True, required=False)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)

    class Meta(SportsmanRegisterSerializer.Meta):
        extra_kwargs = {
            **SportsmanRegisterSerializer.Meta.extra_kwargs,
            "educations": {"required": False},
            "results": {"required": False},
        }

    def update(self, instance, validated_data):
        educations_data = validated_data.pop("educations", None)
        results_data = validated_data.pop("results", None)
        media_ids = validated_data.pop("media_ids", None)

        # Update basic sportsman profile fields
        for attr, value in validated_data.items():
            if attr == "trainer":
                value = value.trainer_profile
            setattr(instance, attr, value)
        instance.save()

        # Update media associations
        if media_ids:
            media_objects = Media.objects.filter(id__in=media_ids)
            if not media_objects.exists():
                raise_validation_error(message=_("At least one media must be uploaded"))

            for media in media_objects:
                if media.sportsmen.exists() and not media.sportsmen.filter(id=instance.id).exists():
                    raise_validation_error(message=_(f"Media {media.id} is already associated with another sportsman."))
            
            # old_media = instance.media.all()
            # instance.media.clear()

            # # Deleting the old media 
            # for media in old_media:
            #     media.delete()

            instance.media.set(media_objects)

        # Update educations
        if educations_data:
            instance.educations.all().delete()
            for education_data in educations_data:
                Education.objects.create(sportsman_profile=instance, **education_data)

        # Update results
        if results_data:
            instance.results.all().delete()
            for result_data in results_data:
                Result.objects.create(sportsman_profile=instance, **result_data)

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance) # Parent's method is invoked here
        return data
    

class SportsmanSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True)
    results = ResultSerializer(many=True)
    media = MediaSerializer(many=True)
    sport = SportSerializer(many=False)

    class Meta:
        model = Sportsman
        fields = [
            "sport_type",
            "sport",
            "about_me",
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
            "telegram",
            "instagram",
            "educations",
            "media",
            "results",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["moving_date_month"] = str(instance.moving_date.month).zfill(2)
        data["moving_date_year"] = str(instance.moving_date.year)
        if instance.trainer:
            data["trainer_id"] = instance.trainer.user.id
            data["trainer_name"] = f'{instance.trainer.user}'
        data.pop("moving_date", None)
        return data
    

class TrainerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "user_role",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.trainer_profile.sport:
            data["sport"] = instance.trainer_profile.sport.name
        return data


class TrainerRegisterSerializer(serializers.ModelSerializer):
    educations = EducationCreateSerializer(many=True, required=True)
    results = ResultCreateSerializer(many=True, required=True)
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    moving_date_year = serializers.IntegerField(write_only=True)
    moving_date_month = serializers.IntegerField(write_only=True)
    media = MediaSerializer(many=True, required=False)

    class Meta:
        model = Trainer
        fields = [
            "id",
            "sport_id",
            "sport_type",
            "about_me",
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

        if year and month:
            if not (1 <= month <= 12):
                raise_validation_error("Invalid month. It must be between 1 and 12.")
            
            try:
                attrs["moving_date"] = date(year, month, 1)
            except ValueError:
                raise_validation_error(message=_("Invalid year or month."))
        return attrs
    
    def create(self, validated_data):
        educations_data = validated_data.pop("educations", None)
        results_data = validated_data.pop("results", None)
        media_ids = validated_data.pop("media_ids", None)
        sport = validated_data.pop("sport", None)

        profile = Trainer.objects.create(sport=sport, **validated_data)


        if media_ids:
            # Link existing media to the trainer profile
            media_objects = Media.objects.filter(id__in=media_ids)
            
            if not media_objects.exists():
                raise_validation_error(message=_(f"At least one media must be uploaded"))

            # Check if medias are not associated with another objects
            for media in media_objects:
                if media.trainer.exists() and not media.trainer.filter(id=profile.id).exists():
                    raise_validation_error(message=_(f"Media {media.id} is already associated with another trainer."))

            profile.media.set(media_objects)

        for education_data in educations_data:
            Education.objects.create(trainer_profile=profile, **education_data)
        
        for result_data in results_data:
            Result.objects.create(trainer_profile=profile, **result_data)
        
        logger.info(f"Trainer Profile created -> {profile}")
        return profile

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_name"] = instance.sport.name
        data["moving_date_month"] = str(instance.moving_date.month).zfill(2)
        data["moving_date_year"] = str(instance.moving_date.year)
        data.pop("moving_date", None)
        return data


class TrainerUpdateSerializer(TrainerRegisterSerializer):
    educations = EducationCreateSerializer(many=True, required=False)
    results = ResultCreateSerializer(many=True, required=False)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)

    class Meta(TrainerRegisterSerializer.Meta):
        extra_kwargs = {
            **TrainerRegisterSerializer.Meta.extra_kwargs,
            'educations': {"required": False},
            "results": {"required": False},
        }
    
    def update(self, instance, validated_data):
        educations_data = validated_data.pop("educations", None)
        results_data = validated_data.pop("results", None)
        media_ids = validated_data.pop("media_ids", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update media associations
        if media_ids:
            
            media_objects = Media.objects.filter(id__in=media_ids)
            if not media_objects.exists():
                raise_validation_error(message=_("At least one media must be uploaded"))

            for media in media_objects:
                if media.sportsmen.exists() and not media.sportsmen.filter(id=instance.id).exists():
                    raise_validation_error(message=_(f"Media {media.id} is already associated with another sportsman."))

            instance.media.set(media_objects) 
        
        # Update educations
        if educations_data:
            instance.educations.all().delete()
            for education_data in educations_data:
                Education.objects.create(trainer_profile=instance, **education_data)

        # Update results
        if results_data:
            instance.results.all().delete()
            for result_data in results_data:
                Result.objects.create(trainer_profile=instance, **result_data)

        return instance
    
    def to_representation(self, instance):
        data = super().to_representation(instance) # Parent's method is invoked here
        return data
    

class TrainerSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True)
    results = ResultSerializer(many=True)
    media = MediaSerializer(many=True)
    sport = SportSerializer(many=False)

    class Meta:
        model = Trainer
        fields = [
            "sport_type",
            "sport",
            "about_me",
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
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["moving_date_month"] = str(instance.moving_date.month).zfill(2)
        data["moving_date_year"] = str(instance.moving_date.year)
        data.pop("moving_date", None)
        return data
    

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
    sportsman_profile = SportsmanRegisterSerializer(required=False)
    trainer_profile = TrainerRegisterSerializer(required=False)
    photo_id = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    photo = MediaSerializer(many=True, required=False)
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
            "pinfl",
            "user_role",
            "email",
            "photo_id",
            "photo",
            "birth_date",
            "user_role",
            # "profile",
            "sportsman_profile",
            "trainer_profile",
            "is_verified",
            "created_time",
        )
        extra_kwargs = {
            "id": {"read_only": True}, 
            "is_verified": {"read_only": True}, 
            "photo": {"required": False},
            }

    def validate(self, attrs):
        pinfl = attrs.get("pinfl", None)
        user_role = attrs.get("user_role")
        
        user = User.objects.filter(phone_number=attrs["phone_number"]).first()
        if user:
            raise_validation_error(message=_("Phone number is already registered"))
        
        if user_role != "ordinary":
            if pinfl:
                if User.objects.filter(pinfl=pinfl).exists():
                    raise_validation_error(message=_("PINFL is already registered"))
                if not pinfl.isdigit():
                    raise_validation_error(message=_("PINFL must contain only numbers."))
                if len(pinfl) != 14:
                    raise_validation_error(message=_("PINFL must be exactly 14 digits."))
            else:
                raise_validation_error(message=_("PINFL is required"))
        
        return attrs

    def create(self, validated_data):
        user_role = validated_data.get("user_role")
        sportsman_profile_data = validated_data.pop("sportsman_profile", None)
        trainer_profile_data = validated_data.pop("trainer_profile", None)
        photo_id = validated_data.pop("photo_id", None)
        # profile_data = validated_data.pop("profile", None)
        # print(profile_data)

        with transaction.atomic():
            user = User.objects.create(**validated_data)
            if photo_id:
                media_object = Media.objects.filter(id__in=photo_id)
                user.photo.set(media_object)
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
        # data["photo"] = [photo.file.url for photo in instance.photo.all()]
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
    sportsman_profile = SportsmanUpdateSerializer(required=False)
    trainer_profile = TrainerUpdateSerializer(required=False)
    photo_id = serializers.UUIDField(format='hex_verbose', write_only=True, required=False)
    photo = MediaSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "pinfl",
            "phone_number",
            "email",
            "birth_date",
            "photo_id",
            "photo",
            "user_role",
            "sportsman_profile",
            "trainer_profile",
        ]
        extra_kwargs = {"id": {"read_only": True}}

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")
        pinfl = attrs.get("pinfl", None)
        user_role = attrs.get("user_role")

        # Checking if phone_number is being updated
        if phone_number and self.instance.phone_number != phone_number:
            # Looking for other users with the same phone number
            if User.objects.filter(phone_number=phone_number).exists():
                raise_validation_error(message=_("Phone number is already registered"))

        if user_role != "ordinary":
            if pinfl:
                if self.instance.pinfl != pinfl:
                    if User.objects.filter(pinfl=pinfl).exists():
                        raise_validation_error(message=_("PINFL is already registered"))
                if not pinfl.isdigit():
                    raise_validation_error(message=_("PINFL must contain only numbers."))
                if len(pinfl) != 14:
                    raise_validation_error(message=_("PINFL must be exactly 14 digits."))
            
        return attrs

    def update(self, instance, validated_data):
        photo_id = validated_data.pop("photo_id", None)
        sportsman_profile_data = validated_data.pop("sportsman_profile", None)
        trainer_profile_data = validated_data.pop("trainer_profile", None)

        with transaction.atomic():
            # Updating user fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if photo_id:
                current_photos = instance.photo.all()
                instance.photo.clear()
                current_photos.delete()
                media_objects = Media.objects.get(id=photo_id)
                instance.photo.add(media_objects)

            if sportsman_profile_data:
                spotrsman_profile = getattr(instance, "sportsman_profile", None)
                if spotrsman_profile:
                    SportsmanUpdateSerializer().update(spotrsman_profile, sportsman_profile_data)

            if trainer_profile_data:
                trainer_profile = getattr(instance, "trainer_profile", None)
                if trainer_profile:
                    TrainerUpdateSerializer().update(trainer_profile, trainer_profile_data)

        return instance
    
