from django.utils.translation import gettext_lazy as _

from apps.user.models import (
    User,
    UserRequest,
)
from apps.shared.utils.notifications import send_notification_to_user
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.logging import logger
import apps.shared.utils.enums as enums
from apps.sport.models import Result


class UserRequestService:
    @staticmethod
    def create_request(sender, receivers, request_type, federation=None, data=None, message=None):
        # Prevent duplicates
        if UserRequest.objects.filter(
            sender=sender,
            status=enums.UserRequestStatus.PENDING.value,
            request_type=request_type,
            federation=federation
        ).exists():
            return None, _("You already have a pending request!"), False

        # Create request
        user_request = UserRequest.objects.create(
            sender=sender,
            request_type=request_type,
            status=enums.UserRequestStatus.PENDING.value,
            federation=federation,
            data=data or {},
            message=message or ""
        )
        user_request.receivers.set(receivers)

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
        if request_type == enums.UserRequestTypes.TRAINER_REQUEST.value:
            return UserRequestService._handle_trainer_request(user_request, validated_data, receiver)
        elif request_type == enums.UserRequestTypes.FEDERATION_REQUEST.value:
            return UserRequestService._handle_federation_request(user_request, validated_data, receiver)
        elif request_type == enums.UserRequestTypes.FEDERATION_ADMIN_REQUEST.value:
            return UserRequestService._handle_federation_admin_request(user_request, validated_data, receiver)
        elif request_type == enums.UserRequestTypes.SPORTSMAN_RESULT_VERIFICATION_REQUEST.value:
            return UserRequestService._handle_result_verification_request(user_request, validated_data, receiver)
        return _("Invalid request type!"), False

    @staticmethod
    def _handle_trainer_request(user_request, validated_data, receiver):
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
                    "request_type": "trainer_request",
                    "trainer_id": str(receiver.id),
                }
                UserRequestService.accept_request(user_request, notification_body, notification_data)
            else:
                return _("Receiver must be a valid trainer!"), False
        else:
            notification_body = f"{receiver.full_name} has declined your request."
            notification_data = {
                "request_type": "trainer_request",
                "trainer_id": str(receiver.id),
            }
            UserRequestService.decline_request(user_request, notification_body, notification_data)
        return _("Request handled successfully."), True

    @staticmethod
    def _handle_federation_request(user_request, validated_data, receiver):
        status = validated_data.get("status")
        sender = user_request.sender
        logger.info(f"Receiver (federation): {receiver}")  # LOGGING
        if user_request.status == enums.UserRequestStatus.PENDING.value and status == enums.UserRequestStatus.ACCEPTED.value:
            # If the request is accepted, update the federation for the sender
            if receiver:
                sender.trainer_profile.federation = receiver.federation
                sender.trainer_profile.is_trainer_verified = True
                sender.trainer_profile.save()
                notification_body = f"{receiver.federation.name} has accepted your request."
                notification_data = {
                    "request_type": "federation_request",
                    "federation_id": str(receiver.federation.id),
                }
                UserRequestService.accept_request(user_request, notification_body, notification_data)
            else:
                return _("Receiver must be a valid federation!"), False
        else:
            notification_body = f"{receiver.federation.name} has declined your request."
            notification_data={
                "request_type": "federation_request",
                "federation_id": str(receiver.federation.id),
            }
            UserRequestService.decline_request(user_request, notification_body, notification_data)
        return _("Request handled successfully."), True

    def _handle_federation_admin_request(user_request, validated_data, receiver):
        status = validated_data.get("status")
        sender = user_request.sender
        logger.info(f"Receiver (federation admin): {receiver}")  # LOGGING
        if user_request.status == enums.UserRequestStatus.PENDING.value and status == enums.UserRequestStatus.ACCEPTED.value:
            # If the request is accepted, update the federation for the sender
            if receiver:
                logger.info(f"Receiver federation: {receiver.federation}")  # LOGGING
                sender.federations.add(receiver.federation)
                sender.save()
                notification_body = f"{receiver.federation.name} has accepted your request."
                notification_data = {
                    "request_type": "federation_admin_request",
                    "federation_id": str(receiver.federation.id),
                }
                UserRequestService.accept_request(user_request, notification_body, notification_data)
            else:
                return _("Receiver must be a valid federation!"), False
        else:
            notification_body = f"{receiver.federation.name} has declined your request."
            notification_data = {
                "request_type": "federation_admin_request",
                "federation_id": str(receiver.federation.id),
            }
            UserRequestService.decline_request(user_request, notification_body, notification_data)
        return _("Request handled successfully."), True

    def _handle_result_verification_request(user_request, validated_data, receiver):
        status = validated_data.get("status")
        logger.info(f"Receiver (sportsman result verification): {receiver}")  # LOGGING
        if user_request.status == enums.UserRequestStatus.PENDING.value and status == enums.UserRequestStatus.ACCEPTED.value:
            # If the request is accepted, update the result for the sender
            if receiver:
                result_id = user_request.data.get("result_id")
                sportsman_result = Result.objects.filter(id=result_id).first()
                sportsman_result.is_verified = True
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
            notification_body = f"{receiver.full_name} has declined your request."
            notification_data = {
                "request_type": "sportsman_result_verification_request",
                "result_id": str(result_id),
            }
            UserRequestService.decline_request(user_request, notification_body, notification_data)
        return _("Request handled successfully."), True
