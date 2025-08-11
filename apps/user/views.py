from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from fcm_django.models import FCMDevice

import rest_framework_simplejwt.views as simplejwt_views
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, permissions, status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.filters import SearchFilter, OrderingFilter

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.user.filters import (
    SportsmanFilter,
    TrainerFilter,
    UserNotificationFilter,
    UserRequestFilter,
    DistrictFilter,
    NeighborhoodFilter
)
from apps.user.models import (
    User,
    ArchivedTrainer,
    UserMedia,
    UserNotification,
    UserRequest
)
from apps.shared.models import (
    Region,
    District,
    Neighborhood
)

import apps.user.serializers as serializers
from apps.shared.utils.pagination import CustomPagination
from apps.shared.utils.verification import (
    send_verification_code,
    verify_code,
    check_verification_status,
)
from apps.shared.utils.utils import (
    success_response,
    error_response,
)
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.redis_utils import get_redis_connection
from apps.shared.utils.logging import logger
from apps.shared.utils import enums
from apps.shared.utils.permissions import IsAdminOrSuperAdmin


redis_connection = get_redis_connection()


class SendVerificationCodeView(generics.CreateAPIView):
    throttle_classes = (AnonRateThrottle,)
    permission_classes = (permissions.AllowAny,)
    serializer_class = serializers.SendVerificationCodeSerializer

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
    serializer_class = serializers.VerifyCodeSerializer

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
        logger.info(f"Status code: {response_code}, Message: {message}")
        if response_code == 200:
            return success_response(
                message=_(message),
                data=data,
            )
        return error_response(message=_("Confirmation code is incorrect"))


class RegistrationView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()
    serializer_class = serializers.SelfRegistrationSerializer

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
    serializer_class = serializers.CustomTokenRefreshSerializer

    def post(self, request: Request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return success_response(
            data=response.data, message=_("Token refreshed successfully")
        )
    

class LogoutView(APIView):
    serializer_class = serializers.LogoutSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request: Request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            FCMDevice.objects.filter(
                user=request.user,
                registration_id=serializer.validated_data.get("fcm_token", ""),
            ).update(active=False)
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
    serializer_class = serializers.UserUpdateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializers.UsersMeSerializer
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
            data=serializers.UsersMeSerializer(user, context={"request": request}).data,
        )


class ChangePasswordView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.ChangePasswordSerializer
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
    serializer_class = serializers.UpdatePhoneNumberSerializer
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
    serializer_class = serializers.VerifyCodeSerializer
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
    permission_classes = (IsAdminOrSuperAdmin,)
    serializer_class = serializers.RegistrationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SportsmanFilter
    #pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializers.SportsmanListSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # Pass the request to the serializer
        return context
    
    def get_queryset(self):
        queryset = User.objects.filter(user_role='sportsman').select_related(
            'sportsman_profile__sport', 'sportsman_profile__trainer', 
        )
        return queryset

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sportsman created successfully"),
            code=status.HTTP_201_CREATED
        )
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Sportsman list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class SportsmanRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = User.objects.all().select_related(
        "sportsman_profile", "sportsman_profile__sport", "sportsman_profile__trainer"
    ).prefetch_related("media", "educations", "results")
    serializer_class = serializers.UserUpdateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializers.UsersMeSerializer # Because I am assigning sportsman or trainer profile during presentation by looking into user_role
        return super().get_serializer_class()

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_object(self):
        user_profile = self.queryset.filter(pk=self.kwargs.get("pk")).first()
        if not user_profile:
            raise_validation_error(message=_("Sportsman Profile not found"), code=status.HTTP_404_NOT_FOUND)
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
    permission_classes = (IsAdminOrSuperAdmin, )
    queryset = User.objects.all()
    serializer_class = serializers.RegistrationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TrainerFilter
    #pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializers.TrainerListSerializer
        return super().get_serializer_class()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # Pass the request to the serializer
        return context

    def get_queryset(self):
        queryset = User.objects.filter(user_role='trainer').prefetch_related(
            "trainer_profile__sport",
        )
        return queryset
    
    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(), )
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Trainer created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Trainer list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class TrainerRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = User.objects.all().select_related(
        "trainer_profile", "trainer_profile__sport"
    ).prefetch_related("media", "educations", "results")
    serializer_class = serializers.UserUpdateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_Class = TrainerFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializers.UsersMeSerializer # Because I am assigning sportsman or trainer profile during presentation by looking into user_role
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

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

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
    serializer_class = serializers.BaseMediaSerializer

    def get_queryset(self):
        model_type = self.request.data.get("type")
        model = self.get_model(model_type=model_type)
        return model.objects.all() if model else UserMedia.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # Pass the request to the serializer
        model_type = self.request.data.get("type") # user, sportcomplex # 
        if model_type:
            context["model"] = self.get_model(model_type=model_type)
        self.request.data.pop("type")
        return context

    def create(self, request, *args, **kwargs):
        data = request.data
        is_profile_photo = data.get("is_profile_photo", "false").lower() == "true"
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
    serializer_class = serializers.BaseMediaSerializer

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
    serializer_class = serializers.ArchivedTrainerSerializer

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
    serializer_class = serializers.ArchivedTrainerSerializer

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


class UserNotificationsListView(generics.ListAPIView):
    queryset = UserNotification.objects.all()
    serializer_class = serializers.UserNotificationSerializer
    pagination_class = CustomPagination
    permission_classes = [permissions.IsAuthenticated,]
    filterset_class = UserNotificationFilter
    search_fields = ["id", "title", "text",]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    ordering_fields = ["id", "created_time", "is_read", "title",]

    def get_queryset(self):
        return UserNotification.objects.filter(user=self.request.user).order_by("-created_time")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return success_response(data=response.data, message=_("Bildirishnomalar ro'yxati"), code=status.HTTP_200_OK)


class UserNotificationMarkAsReadView(generics.UpdateAPIView):
    queryset = UserNotification.objects.all()
    serializer_class = serializers.UserNotificationSerializer
    permission_classes = [permissions.IsAuthenticated,]

    def get_object(self):
        notification = UserNotification.objects.filter(id=self.kwargs.get("notification_id"), user=self.request.user).first()
        if not notification:
            return raise_validation_error(message=_("Bildirishnoma topilmadi"), code=status.HTTP_404_NOT_FOUND)
        return notification

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_read = True
        instance.save(update_fields=["is_read"])
        return success_response(
            data=self.get_serializer(instance).data,
            message=_("Bildirishnoma muvaffaqiyatli yangilandi"),
            code=status.HTTP_200_OK
        )


class UserRequestListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = UserRequest.objects.all()
    serializer_class = serializers.UserRequestSerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = CustomPagination
    filterset_class = UserRequestFilter
    filter_backends = [OrderingFilter, DjangoFilterBackend, SearchFilter]
    search_fields = [
        "sender__first_name",
        "sender__last_name",
        "receiver__first_name",
        "receiver__last_name",
        "request_type",
        "message",
    ]

    def _get_proper_message(self, request_type):
        if request_type == "trainer_request":
            return _("You cannot create a new request while you have a pending trainer request.")
        elif request_type == "federation_request":
            return _("You cannot create a new request while you have a pending federation request.")

    def get_queryset(self):
        req_type = self.request.query_params.get("type")
        if req_type == "sent":
            return UserRequest.objects.filter(sender=self.request.user)
        elif req_type == "received":
            return UserRequest.objects.filter(receiver=self.request.user)
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        request_type = request.data['request_type']
        if self.get_queryset().filter(status=enums.UserRequestStatus.PENDING.value).exists():
            raise_validation_error(message=self._get_proper_message(request_type))
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("User Request successfully created"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("User Request list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class UserRequestRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = UserRequest.objects.all()
    serializer_class = serializers.UserRequestSerializer

    def get_object(self):
        user_request = self.queryset.filter(pk=self.kwargs.get("pk")).first()
        if not user_request:
            raise_validation_error(message=_("User Request not found"), code=status.HTTP_404_NOT_FOUND)
        return user_request

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data, 
            message=_("User Request retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request: Request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data, 
            message=_("User Request updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("User Request deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class RegionListView(generics.ListAPIView):
    queryset = Region.objects.all()
    serializer_class = serializers.RegionSerializer
    permission_classes = [permissions.AllowAny, ]
    pagination_class = CustomPagination
    search_fields = ["id", "name"]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Region list retrieved successfully"),
            code=status.HTTP_200_OK
        )
    

class DistrictListView(generics.ListAPIView):
    queryset = District.objects.all()
    serializer_class = serializers.DistrictSerializer
    permission_classes = [permissions.AllowAny, ]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["id", "name", "region__name"]
    filterset_class = DistrictFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("District list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class NeighborhoodListView(generics.ListAPIView):
    queryset = Neighborhood.objects.all()
    serializer_class = serializers.NeighborhoodSerializer
    permission_classes = [permissions.AllowAny, ]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["id", "name", "district__name"]
    filterset_class = NeighborhoodFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Neighborhood list retrieved successfully"),
            code=status.HTTP_200_OK
        )
