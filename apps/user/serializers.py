from datetime import date
from django.contrib.auth import authenticate
from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

import rest_framework_simplejwt.tokens as jwt_tokens
import rest_framework_simplejwt.serializers as jwt_serializers

from typing import List, Dict, Any

# custom
from shared.addons.custom_logging import logger
from shared.addons.exceptions import raise_validation_error
from shared.addons.utils import CorrectPath
from shared.addons.send_verification import (
    send_verification_code,
    verify_code,
    check_verification_status,
)
from .utils import calculate_sportsman_statistics, calculate_trainer_statistics

from user.models import (
    User,
    Sportsman,
    Trainer,
    ArchivedTrainer,
    UserMedia
)

from sport.models import (
    Sport,
    Tournament,
    Result
)

from education.models import (
    Education
)

from sport.serializers import (
    ResultCreateSerializer,
    SportSerializer
)

from education.serializers import (
    EducationCreateSerializer
)


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


class BaseMediaSerializer(serializers.ModelSerializer): # need to be updated
    type = serializers.ChoiceField(
        choices=(
            ("sportsman", "sportsman"), 
            ("trainer", "trainer"), 
            ("user", "user"), 
            ), 
            write_only=True
    )

    class Meta:
        model = UserMedia
        fields = (
            "id", 
            "media_type", 
            "size", 
            "extension", 
            "created_time", 
            "file", 
            "type" 
        )
        read_only_fields = ["created_time", "size", "extension", "media_type"]

    def validate(self, data):
        """
        Validate the file size for PDFs
        """
        file = data.get("file")
        if file:
            if file.name.lower().endswith(".pdf"):
                if file.size > settings.MAX_PDF_SIZE_BYTES:
                    size_in_mb = file.size / (1024 * 1024)
                    raise_validation_error(
                        message=_(f"PDF files must be less than 10 MB. Current one is {size_in_mb:.2f}")
                    )
        return data

    def create(self, validated_data):
        type = validated_data.pop("type", None)
        model = self.context.get("model")
        media_instance = model(**validated_data)

        if type:
            correct_path = CorrectPath('media', owner=type)
            media_instance.file.field.upload_to = correct_path
        media_instance.save()
        return media_instance


class UsersMeSerializer(serializers.ModelSerializer): # need to be updated
    media = BaseMediaSerializer(many=True)
    educations = EducationCreateSerializer(many=True, required=False)
    results = ResultCreateSerializer(many=True, required=False)

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
            "gender",
            "birth_date",
            "is_superuser",
            "media",
            "educations",
            "results",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.user_role == "sportsman":
            data["sportsman_profile"] = SportsmanProfileSerializer(instance.sportsman_profile, context=self.context).data
        elif instance.user_role == "trainer":
            data["trainer_profile"] = TrainerProfileSerializer(instance.trainer_profile, context=self.context).data
        return data


class SportsmanListSerializer(serializers.ModelSerializer):
    statistics = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "user_role",
            "statistics"
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if instance.sportsman_profile.sport:
            data["sport"] = instance.sportsman_profile.sport.name
            if instance.sportsman_profile.sport.logo:
                data["logo"] = request.build_absolute_uri(instance.sportsman_profile.sport.logo.url)
        if instance.sportsman_profile.trainer:
            data["trainer_id"] = instance.sportsman_profile.trainer.user_id
            data["trainer_name"] = f'{instance.sportsman_profile.trainer.user}'
        return data
    
    def get_statistics(self, obj) -> Dict[str, Any]:
        return calculate_sportsman_statistics(sportsman=obj)

    

class SportsmanProfileCreateSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True)
    trainer_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source="trainer", write_only=True, required=False)

    class Meta:
        model = Sportsman
        fields = [
            "sport_id",
            "trainer_id",
            "skill_level",
            "bio",
            "division",
            "user_metrics",
            "address",
            "social_media",
        ]

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        sport = validated_data.get("sport", None)
        trainer = validated_data.get("trainer", None)
        if trainer and hasattr(trainer, "trainer_profile") and trainer.trainer_profile:
            trainer_profile = trainer.trainer_profile
            if trainer_profile.sport.id != sport.id:
                raise_validation_error(message=_(f"Trainer's sport must be equal to sportsman's sport"))

        return validated_data

    def create(self, validated_data):
        sport = validated_data.pop("sport", None)
        trainer = validated_data.pop("trainer", None)
        profile = Sportsman.objects.create(sport=sport, trainer=trainer.trainer_profile, **validated_data)
        logger.info(f"Sportsman Profile created -> {profile}")

        return profile
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_name"] = instance.sport.name
        if instance.trainer:
            logger.info(f"Trainer id: {instance.trainer.user}")
            data["trainer_id"] = instance.trainer.user_id
            data["trainer_name"] = f'{instance.trainer.user}'
        return data


class SportsmanProfileUpdateSerializer(SportsmanProfileCreateSerializer):
    
    def update(self, instance, validated_data):
        sport = validated_data.pop("sport", None)
        trainer = validated_data.pop("trainer", None)

        if sport:
            instance.sport = sport
        if trainer:
            instance.trainer = trainer.trainer_profile

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        
        return instance
    

class SportsmanProfileSerializer(serializers.ModelSerializer):
    sport = SportSerializer(many=False, read_only=True)
    statistics = serializers.SerializerMethodField()

    class Meta:
        model = Sportsman
        fields = [
            "sport",
            "skill_level",
            "bio",
            "division",
            "user_metrics",
            "address",
            "social_media",
            "statistics"
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.trainer:
            data["trainer_id"] = instance.trainer.user_id
            data["trainer_name"] = f'{instance.trainer.user}'
        return data
    
    def get_statistics(self, obj) -> Dict[str, Any]:
        return calculate_sportsman_statistics(sportsman=obj.user)
    

class TrainerListSerializer(serializers.ModelSerializer):
    statistics = serializers.SerializerMethodField()
    # logo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "user_role",
            "statistics",
            # "logo",
        ]
    
    def to_representation(self, instance): 
        data = super().to_representation(instance)
        request = self.context.get("request")
        if instance.trainer_profile.sport:
            data["sport"] = instance.trainer_profile.sport.name
            if instance.trainer_profile.sport.logo:
                data["logo"] = request.build_absolute_uri(instance.trainer_profile.sport.logo.url)
        return data
    
    def get_statistics(self, obj) ->  List[Dict[str, Any]]:
        return calculate_trainer_statistics(trainer=obj)

    

class TrainerProfileCreateSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source="sport", write_only=True)

    class Meta:
        model = Trainer
        fields = [
            "sport_id",
            "skill_level",
            "bio",
            "division",
            "user_metrics",
            "address",
            "social_media",
        ]
    
    def create(self, validated_data):
        sport = validated_data.pop("sport", None)
        
        
        profile = Trainer.objects.create(sport=sport, **validated_data)
        logger.info(f"Trainer Profile created -> {profile}")
    
        return profile

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_name"] = instance.sport.name
        return data


class TrainerProfileUpdateSerializer(TrainerProfileCreateSerializer):
    
    def update(self, instance, validated_data):
        sport = validated_data.pop("sport", None)

        if sport:
            instance.sport = sport

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance
    

class TrainerProfileSerializer(serializers.ModelSerializer):
    sport = SportSerializer(many=False, read_only=True)
    statistics = serializers.SerializerMethodField()

    class Meta:
        model = Trainer
        fields = [
            "sport",
            "skill_level",
            "bio",
            "division",
            "user_metrics",
            "address",
            "social_media",
            "statistics",
        ]
    
    def get_statistics(self, obj) -> Dict[str, Any]:
        return calculate_trainer_statistics(trainer=obj.user)


class RegistrationSerializer(serializers.ModelSerializer):
    educations = EducationCreateSerializer(many=True, required=True)
    results = ResultCreateSerializer(many=True, required=True)
    sportsman_profile = SportsmanProfileCreateSerializer(required=False)
    trainer_profile = TrainerProfileCreateSerializer(required=False)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    media = BaseMediaSerializer(many=True, required=False)
    
    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "first_name",
            "middle_name",
            "last_name",
            "pinfl",
            "gender",
            "user_role",
            "email",
            "media_ids",
            "media",
            "birth_date",
            "user_role",
            "educations",
            "results",
            "is_verified",
            "sportsman_profile",
            "trainer_profile",
            "created_time",
        )
        extra_kwargs = {
            "id": {"read_only": True}, 
            "is_verified": {"read_only": True}, 
            "media_ids": {"required": False},
            }
    
    # def get_media(self, instance):
    #     queryset = instance.media.all()
    #     return BaseMediaSerializer(queryset, many=True).data()

    def validate(self, attrs):
        pinfl = attrs.get("pinfl", None)
        user_role = attrs.get("user_role")
        
        phone_number = attrs.get("phone_number")
        if phone_number:
            if User.objects.filter(phone_number=phone_number).exists() :
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
        educations_data = validated_data.pop("educations", None)
        results_data = validated_data.pop("results", None)
        user_role = validated_data.get("user_role")
        sportsman_profile_data = validated_data.pop("sportsman_profile", None)
        trainer_profile_data = validated_data.pop("trainer_profile", None)
        media_ids = validated_data.pop("media_ids", None)

        with transaction.atomic():
            user = User.objects.create(**validated_data)
            if media_ids:
                media_objects = UserMedia.objects.filter(id__in=media_ids)
                
                if not media_objects.exists():
                    raise_validation_error(message=_(f"At least one media must be uploaded"))
                
                # Check for media linked to other users
                if media_objects.exclude(user__isnull=True).exists():
                    raise_validation_error(message=_("One or more media are already associated with another user."))

                user.media.set(media_objects)
            logger.info(f"User created -> {user}")
            
            # Bulk create educations
            if educations_data:
                Education.objects.bulk_create([
                    Education(user=user, **ed_data) for ed_data in educations_data
                ])
            
            # create() inside the loop, because has to trigger signal!
            for result_data in results_data:
                if 'archived_trainer_name' in result_data:
                    archived_trainer_name = result_data.pop('archived_trainer_name')
                    if archived_trainer_name:
                        ArchivedTrainerSerializer().validate(attrs={"name": archived_trainer_name})
                        archived_trainer = ArchivedTrainer.objects.create(name=archived_trainer_name)
                        result_data['archived_trainer'] = archived_trainer
                Result.objects.create(user=user, **result_data)

            if user_role == "sportsman" and sportsman_profile_data:
                sportsman_profile_data['trainer'] = sportsman_profile_data.get('trainer').trainer_profile
                Sportsman.objects.create(user=user, **sportsman_profile_data)
            elif user_role == "trainer" and trainer_profile_data:
                Trainer.objects.create(user=user, **trainer_profile_data)
            
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
    sportsman_profile = SportsmanProfileUpdateSerializer(required=False)
    trainer_profile = TrainerProfileUpdateSerializer(required=False)
    media_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    media = BaseMediaSerializer(many=True, required=False)
    educations = EducationCreateSerializer(many=True, required=False)
    results = ResultCreateSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "pinfl",
            "phone_number",
            "gender",
            "email",
            "birth_date",
            "media_ids",
            "media",
            "user_role",
            "educations",
            "results",
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
        educations_data = validated_data.pop("educations", None)
        results_data = validated_data.pop("results", None)
        media_ids = validated_data.pop("media_ids", None)
        sportsman_profile_data = validated_data.pop("sportsman_profile", None)
        trainer_profile_data = validated_data.pop("trainer_profile", None)

        with transaction.atomic():
            # Updating user fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if media_ids:
                media_objects = UserMedia.objects.filter(id__in=media_ids)
                if not media_objects.exists():
                    raise_validation_error(message=_("At least one media must be uploaded"))

                for media in media_objects:
                    if media.user.exists() and not media.user.filter(id=instance.id).exists():
                        raise_validation_error(message=_(f"Media {media.id} is already associated with another sportsman."))
            
                current_media = instance.media.all() # Get current media 
                media_to_delete = current_media.exclude(id__in=media_ids)

                for media in media_to_delete:
                    # Disassociate the media from the current sportsman
                    instance.media.remove(media)
                    media.file.delete()  # Delete the file from the file system
                    media.delete()  # Delete the Media object from the database

                # Associate the new media objects
                instance.media.set(media_objects)
            else:
                # If media_ids is None, remove all existing media associations
                current_media = instance.media.all()
                for media in current_media:
                    # Disassociate the media from the current sportsman
                    instance.media.remove(media)
                    media.file.delete()  # Delete the file from the file system
                    media.delete()  # Delete the Media object from the database

                # Clear all media associations for the instance
                instance.media.clear()

            if educations_data:
                instance.educations.all().delete()
                for education_data in educations_data:
                    Education.objects.create(user=instance, **education_data)

            if results_data:
                instance.results.all().delete()
                for result_data in results_data:
                    if 'archived_trainer_name' in result_data:
                        archived_trainer_name = result_data.pop('archived_trainer_name')
                        if archived_trainer_name:
                            ArchivedTrainerSerializer().validate(attrs={"name": archived_trainer_name})
                            archived_trainer = ArchivedTrainer.objects.create(name=archived_trainer_name)
                            result_data['archived_trainer'] = archived_trainer
                    Result.objects.create(user=instance, **result_data)

            if sportsman_profile_data:
                spotrsman_profile = getattr(instance, "sportsman_profile", None)
                if spotrsman_profile:
                    SportsmanProfileUpdateSerializer().update(spotrsman_profile, sportsman_profile_data)

            if trainer_profile_data:
                trainer_profile = getattr(instance, "trainer_profile", None)
                if trainer_profile:
                    TrainerProfileUpdateSerializer().update(trainer_profile, trainer_profile_data)

        return instance

class ArchivedTrainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivedTrainer
        fields = ["id", "name"]
        extra_kwargs = {"id": {"read_only": True}}

    def validate(self, attrs):
        name = attrs.get('name', None)
        
        if name:
            if ArchivedTrainer.objects.filter(name=name).exists():
                raise_validation_error(message=_("Archived Trainer with this name already exists"))
        
        return attrs
