from django.contrib.auth import authenticate
from django.db import IntegrityError
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
    Education,
    Result,
    Media,
)

from shared.addons.exceptions import raise_validation_error
from shared.addons.utils import CorrectPath
from shared.addons.send_verification import (
    send_verification_code,
    verify_code,
    check_verification_status,
)

from dashboard.serializers import (
    SportsmanRegisterSerializer,
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


class RegistrationSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField()
    sportsman_profile = SportsmanRegisterSerializer(required=False)
    
    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "first_name",
            "middle_name",
            "last_name",
            "user_role",
            "photo",
            "birth_date",
            "user_role",
            "sportsman_profile",
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
        sportsman_profile_data = validated_data.pop("sportsman_profile", None)

        user = User.objects.create(**validated_data)
        if validated_data.get("user_role") == "sportsman" and sportsman_profile_data:
            sportsman_profile_data["user"] = user
            SportsmanRegisterSerializer().create(sportsman_profile_data)

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





