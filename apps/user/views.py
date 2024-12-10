from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, permissions, status, filters

import rest_framework_simplejwt.views as simplejwt_views
from rest_framework_simplejwt.exceptions import TokenError


from shared.addons.pagination import CustomPagination
from shared.addons.send_verification import (
    send_verification_code,
    verify_code,
    check_verification_status,
)
from shared.addons.utils import (
    success_response,
    error_response,
)

from .models import (
    User,
)

from .serializers import (
    SendVerificationCodeSerializer,
    VerifyCodeSerializer,
    RegistrationSerializer,
    LogoutSerializer,
    UsersMeSerializer,
    ChangePasswordSerializer,
    UpdatePhoneNumberSerializer,
    CustomTokenRefreshSerializer,
    UserUpdateSerializer
)

from shared.addons.redis_utils import get_redis_connection

redis_connection = get_redis_connection()


class SendVerificationCodeView(generics.CreateAPIView):
    throttle_classes = (AnonRateThrottle,)
    permission_classes = (permissions.AllowAny,)
    serializer_class = SendVerificationCodeSerializer

    def post(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code, message = send_verification_code(
            serializer.validated_data["phone_number"]
        )

        if code == 200:
            return success_response(message=_(message))

        return error_response(message=_(message))


class VerifyCodeView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = VerifyCodeSerializer

    def post(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        phone_number: str = data.get("phone_number", None)
        code: str = data.get("code")

        response_code, message = verify_code(phone_number, code)
        print(f"response code: {response_code}, message: {message}")
        # if response_code == 200:
        #     if data["action"] == "signup":
        #         user, created = User.objects.get_or_create(
        #             phone_number=phone_number, is_verified=True
        #         )
        #         data["tokens"] = user.tokens()
        #     return success_response(message=_(message), data=data)
        if response_code == 200:
            return success_response(
                message=_(message),
                data=data,
            )
        return error_response(message=_("Confirmation code is incorrect"))


class RegistrationView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()
    serializer_class = RegistrationSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number: str = serializer.validated_data.get("phone_number", None)
        is_verified, message = check_verification_status(phone_number)

        if is_verified:
            serializer.save(is_verified=True)
            return success_response(
                data=serializer.data, message=_("User registration successful!")
            )
        return error_response(message=_(message))


class LoginRefreshView(simplejwt_views.TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer

    def post(self, request: Request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return success_response(
            data=response.data, message=_("Token refreshed successfully")
        )
    

class LogoutView(APIView):
    serializer_class = LogoutSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request: Request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh_token = self.request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return success_response(
                message=_("You are logged out"),
                code=status.HTTP_205_RESET_CONTENT,
            )
        except TokenError:
            return error_response(
                code=status.HTTP_400_BAD_REQUEST,
                message=_("Invalid refresh token"),
            )
        except Exception as exc:
            return error_response(
                code=status.HTTP_400_BAD_REQUEST,
                message=_("Invalid refresh token"),
                data={"exc_detail": str(exc)},
            )


class UserRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return UsersMeSerializer
        return self.serializer_class

    def get_object(self):
        return User.objects.get(id=self.request.user.id)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data, message=_("User retrieved successfully")
        )

    def update(self, request: Request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return success_response(
            message=_("User updated successfully"),
            data=UsersMeSerializer(user, context={"request": request}).data,
        )


class ChangePasswordView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request: Request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(message=_("Password changed successfully."))


class UserPhoneUpdateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UpdatePhoneNumberSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def post(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data.get("phone_number")
        code, message = send_verification_code(phone_number)
        if code == 200:
            return success_response(message=_(message))
        else:
            return error_response(message=_(message))


class UserPhoneUpdateConfirmView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = VerifyCodeSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def put(self, request: Request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data.get("phone_number")
        code = serializer.validated_data.get("code")
        response_code, message = verify_code(phone_number, code)

        if response_code == 200:
            user.phone_number = phone_number
            user.save()
            return success_response(
                message=_("User phone number is updated successfully")
            )

        return error_response(message=_(message))