import typing as t

from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet, Model
from django.utils.functional import Promise

from apps.user.models import (
    User,
    UserRequest,
)
from apps.federation.models import (
    Federation
)
from apps.shared.utils.types import *
from apps.shared.utils.notifications import send_notification_to_user
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.logging import logger
import apps.shared.utils.enums as enums
from apps.sport.models import Result
from apps.shared.services.scoring_service import ScoringService


class UserRequestService:
    @staticmethod
    def create_request(
        sender: User,
        receivers: QuerySet[User],
        request_type: str,
        federation: t.Optional[Federation] = None,
        old_data: t.Optional[dict] = None,
        new_data: t.Optional[dict] = None,
        metadata: t.Optional[dict] = None,
        message_from_sender: str = "",
        message_from_receiver: str = ""
    ) -> tuple[t.Optional[UserRequest], str | Promise, bool]:

        # Prevent duplicates
        if UserRequest.objects.filter(
            sender=sender,
            status=enums.UserRequestStatus.PENDING.value,
            request_type=request_type,
            federation=federation
        ).exists():
            return None, _("You already have a pending request!"), False

        # Create request
        user_request: UserRequest = UserRequest.objects.create(
            sender=sender,
            request_type=request_type,
            status=enums.UserRequestStatus.PENDING.value,
            federation=federation,
            old_data=old_data or {},
            new_data=new_data or {},
            metadata=metadata or {},
            message_from_sender=message_from_sender
        )
        user_request.receivers.set(receivers)
        logger.info("hello")
        # Notify all receivers
        for receiver in receivers:
            send_notification_to_user(
                user=receiver,
                user_request=user_request,
                title=_("New Request"),
                body=f"{sender.first_name} {sender.last_name} sent you a {request_type.replace('_', ' ').lower()}",
                data={"request_type": request_type}
            )

        return user_request, _("Request created successfully."), True

    @staticmethod
    def accept_request(user_request, notification_body, notification_data):
        user_request.status = enums.UserRequestStatus.ACCEPTED.value
        user_request.save()

        send_notification_to_user(
            user=user_request.sender,
            user_request=user_request,
            title=_("Request Accepted"),
            body=notification_body,
            data=notification_data
        )

    @staticmethod
    def decline_request(user_request, notification_body, notification_data):
        user_request.status = enums.UserRequestStatus.REJECTED.value
        user_request.save()

        send_notification_to_user(
            user=user_request.sender,
            user_request=user_request,
            title=_("Request Rejected"),
            body=notification_body,
            data=notification_data
        )

    @staticmethod
    def handle_request(user_request, validated_data, receiver):
        request_type = user_request.request_type
        if request_type == enums.UserRequestTypes.SPORTSMAN_TRAINER_REQUEST.value:
            return UserRequestService._handle_sportsman_trainer_request(user_request, validated_data, receiver)
        elif request_type == enums.UserRequestTypes.TRAINER_FEDERATION_REQUEST.value:
            return UserRequestService._handle_trainer_federation_request(user_request, validated_data, receiver)
        elif request_type == enums.UserRequestTypes.FEDERATION_ADMIN_REQUEST.value:
            return UserRequestService._handle_federation_admin_request(user_request, validated_data, receiver)
        elif request_type == enums.UserRequestTypes.SPORTSMAN_RESULT_VERIFICATION_REQUEST.value:
            return UserRequestService._handle_result_verification_request(user_request, validated_data, receiver)
        return _("Invalid request type!"), False

    @staticmethod
    def _handle_sportsman_trainer_request(user_request, validated_data, receiver):
        status = validated_data.get("status")
        sender = user_request.sender
        logger.info(f"Receiver (trainer): {receiver}")  # LOGGING
        if user_request.status == enums.UserRequestStatus.PENDING.value and status == enums.UserRequestStatus.ACCEPTED.value:
            # If the request is accepted, update the trainer for the sender
            if receiver and hasattr(receiver, "trainer_profile"):
                sender.sportsman_profile.trainer = receiver.trainer_profile
                sender.sportsman_profile.is_sportsman_verified = True
                sender.sportsman_profile.save()
                notification_body = f"{receiver.full_name} has accepted your request."
                notification_data = {
                    "request_type": "sportsman_trainer_request",
                    "trainer_id": str(receiver.id),
                }
                UserRequestService.accept_request(user_request, notification_body, notification_data)
            else:
                return _("Receiver must be a valid trainer!"), False
        else:
            notification_body = f"{receiver.full_name} has declined your request."
            notification_data = {
                "request_type": "sportsman_trainer_request",
                "trainer_id": str(receiver.id),
            }
            UserRequestService.decline_request(user_request, notification_body, notification_data)
        return _("Request handled successfully."), True

    @staticmethod
    def _handle_trainer_federation_request(user_request, validated_data, receiver):
        status = validated_data.get("status")
        sender = user_request.sender
        logger.info(f"Receiver (federation): {receiver}")  # LOGGING
        federation = user_request.federation
        if user_request.status == enums.UserRequestStatus.PENDING.value and status == enums.UserRequestStatus.ACCEPTED.value:
            # If the request is accepted, update the federation for the sender
            if receiver:
                logger.info(f"Receiver federation: {federation}")  # LOGGING
                sender.trainer_profile.federation = federation
                sender.trainer_profile.is_trainer_verified = True
                sender.trainer_profile.save()
                notification_body = f"{federation.name} has accepted your request."
                notification_data = {
                    "request_type": "trainer_federation_request",
                    "federation_id": str(federation.id),
                }
                UserRequestService.accept_request(user_request, notification_body, notification_data)
            else:
                return _("Receiver must be a valid federation!"), False
        else:
            notification_body = f"{federation.name} has declined your request."
            notification_data = {
                "request_type": "trainer_federation_request",
                "federation_id": str(federation.id),
            }
            UserRequestService.decline_request(user_request, notification_body, notification_data)
        return _("Request handled successfully."), True

    def _handle_federation_admin_request(user_request, validated_data, receiver):
        status = validated_data.get("status")
        sender = user_request.sender
        logger.info(f"Receiver (federation admin): {receiver}")  # LOGGING
        federation = user_request.federation
        if user_request.status == enums.UserRequestStatus.PENDING.value and status == enums.UserRequestStatus.ACCEPTED.value:
            # If the request is accepted, update the federation for the sender
            if receiver:
                logger.info(f"Receiver federation: {federation}")  # LOGGING
                sender.federations.add(federation)
                sender.save()
                notification_body = f"{federation.name} has accepted your request."
                notification_data = {
                    "request_type": "federation_admin_request",
                    "federation_id": str(federation.id),
                }
                UserRequestService.accept_request(user_request, notification_body, notification_data)
            else:
                return _("Receiver must be a valid federation!"), False
        else:
            notification_body = f"{federation.name} has declined your request."
            notification_data = {
                "request_type": "federation_admin_request",
                "federation_id": str(federation.id),
            }
            UserRequestService.decline_request(user_request, notification_body, notification_data)
        return _("Request handled successfully."), True

    def _handle_result_verification_request(user_request, validated_data, receiver):
        status = validated_data.get("status")
        if user_request.status == enums.UserRequestStatus.PENDING.value and status == enums.UserRequestStatus.ACCEPTED.value:
            # If the request is accepted, update the result for the sender
            if receiver:
                sender = user_request.sender

                result_id = user_request.data.get("result_id")
                sportsman_result = Result.objects.filter(id=result_id).first()

                # Applying the requested rating here
                requested_rating = user_request.data.get("requested_rating")
                logger.info(f"Requested rating: {requested_rating}")  # LOGGING
                if requested_rating:
                    ScoringService.update_sportsman_points(
                        sportsman=sender,
                        instance=sportsman_result,
                        tournament=sportsman_result.tournament,
                        rating=requested_rating
                    )
                    sportsman_result.rating = int(requested_rating)

                sender.sportsman_profile.save()
                sportsman_result.is_verified = True
                sportsman_result.status = enums.ResultVerificationStatus.VERIFIED.value
                sportsman_result.save()

                notification_body = f"{receiver.full_name} has accepted your request."
                notification_data = {
                    "request_type": "sportsman_result_verification_request",
                    "result_id": str(result_id),
                }
                UserRequestService.accept_request(user_request, notification_body, notification_data)
            else:
                return _("Receiver must be a valid trainer!"), False
        else:
            result_id = user_request.data.get("result_id")
            sportsman_result = Result.objects.filter(id=result_id).first()
            sportsman_result.status = enums.ResultVerificationStatus.REJECTED.value
            sportsman_result.save()

            notification_body = f"{receiver.full_name} has declined your request."
            notification_data = {
                "request_type": "sportsman_result_verification_request",
                "result_id": str(result_id),
            }
            UserRequestService.decline_request(user_request, notification_body, notification_data)
        return _("Request handled successfully."), True

    @staticmethod
    def build_snapshot(model: ModelT, request_type: str) -> dict:
        """
        Builds a snapshot (dict) of important model fields
        """
        function_mapping: dict[str, t.Callable[[t.Any], dict[str, t.Any]]] = {
            "federation_admin_request": UserRequestService._build_user_federation_snapshot,
        }
        return function_mapping.get(request_type, lambda x: {})(model)

    @staticmethod
    def _build_user_federation_snapshot(user: User) -> dict:
        return {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "birth_date": user.birth_date.isoformat() if user.birth_date else None,
            "email": user.email,
            "user_role": user.user_role,
        }
