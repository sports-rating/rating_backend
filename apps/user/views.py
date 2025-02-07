from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend
from django.http import QueryDict

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, permissions, status, filters

import rest_framework_simplejwt.views as simplejwt_views
from rest_framework_simplejwt.exceptions import TokenError

from user.filters import (
    SportsmanFilter,
    TrainerFilter
    )
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
    Sportsman,
    Trainer,
    ArchivedTrainer,
    UserMedia,
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
    UserUpdateSerializer,
    SportsmanProfileSerializer,
    TrainerProfileSerializer,
    BaseMediaSerializer,
    SportsmanListSerializer,
    TrainerListSerializer,
    ArchivedTrainerSerializer
)

from dashboard.serializers import (
    UserListSerializer
)

from shared.addons.exceptions import raise_validation_error
from shared.addons.redis_utils import get_redis_connection
from shared.addons.custom_logging import logger

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
        # code, message = 200, "Verification code is successfully sent"

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
        # response_code, message = 200, "Verified successfully"
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
    

class SportsmanListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()
    serializer_class = RegistrationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SportsmanFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return SportsmanListSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # Pass the request to the serializer
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sportsman created successfully"),
            code=200
        )
    
    def get_queryset(self):
        return self.queryset.filter(user_role='sportsman')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Sportsman list"),
            code=200
        )


class SportsmanRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return UsersMeSerializer # Because I am assigning sportsman or trainer profile during presentation by looking into user_role
        return super().get_serializer_class()

    def get_object(self):
        user_profile = self.queryset.filter(pk=self.kwargs.get("pk")).first()
        if not user_profile:
            raise_validation_error(message=_("Sportsman Profile not found"), code=404)
        return user_profile            

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # Pass the request to the serializer
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data, 
            message=_("Sportsman retrieved successfully"),
            code=200,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data, 
            message=_("Sportsman profile updated successfully"),
            code=200,
        )
    
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Sportsman deleted successfully"),
            code=204
        )


class TrainerListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny, )
    queryset = User.objects.all()
    serializer_class = RegistrationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TrainerFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return TrainerListSerializer
        return super().get_serializer_class()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # Pass the request to the serializer
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Trainer created successfully"),
            code=200
        )

    def get_queryset(self):
        return self.queryset.filter(user_role='trainer')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Trainer list"),
            code=200
        )


class TrainerRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_Class = TrainerFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return UsersMeSerializer # Because I am assigning sportsman or trainer profile during presentation by looking into user_role
        return super().get_serializer_class()

    def get_object(self):
        user_profile = self.queryset.filter(pk=self.kwargs.get("pk")).first()
        if not user_profile:
            raise_validation_error(message=_("Trainer Profile not found"), code=404)
        return user_profile  

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # Pass the request to the serializer
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data, 
            message=_("Trainer retrieved successfully"),
            code=200,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data, 
            message=_("Trainer profile updated successfully"),
            code=200,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Trainer deleted successfully"),
            code=204
        )


class MediaUploadView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = UserMedia.objects.all()
    serializer_class = BaseMediaSerializer
    
    def get_queryset(self):
        model_type = self.request.data.get("model_type")
        model = self.get_model(model_type=model_type)
        return model.objects.all() if model else UserMedia.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # Pass the request to the serializer
        model_type = self.request.data.get("model_type")
        if model_type:
            context["model"] = self.get_model(model_type=model_type)
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message="Media uploaded successfully",
            code=200
        )
    
    def get_model(self, model_type):
        """
        Returns the appropriate model based on the media type
        """
        model_mapping = {
            "user": UserMedia,
            "other": None
        }
        return model_mapping.get(model_type)


class MediaDeleteView(generics.DestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = UserMedia.objects.all()
    serializer_class = BaseMediaSerializer

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Media deleted successfully"),
            code=204
        )


class ArchivedTrainerCreateListView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = ArchivedTrainer.objects.all()
    serializer_class = ArchivedTrainerSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Archived Trainer created successfully")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Archived Trainer list"),
            code=200
        )


class ArchivedTrainerRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = ArchivedTrainer.objects.all()
    serializer_class = ArchivedTrainerSerializer

    def get_object(self):
        archived_trainer = self.queryset.filter(pk=self.kwargs.get("pk")).first()
        if not archived_trainer:
            raise_validation_error(message=_("Trainer Profile not found"), code=404)
        return archived_trainer  

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data, 
            message=_("Archived Trainer retrieved successfully"),
            code=200,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data, 
            message=_("Archived Trainer profile updated successfully"),
            code=200,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Archived Trainer deleted successfully"),
            code=204
        )
