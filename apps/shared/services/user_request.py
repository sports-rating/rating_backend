from django.utils.translation import gettext_lazy as _

from apps.user.models import (
    User,
    UserRequest,
)
from apps.shared.utils.notifications import send_notification_to_user
from apps.shared.utils.exceptions import raise_validation_error
import apps.shared.utils.enums as enums


class UserRequestService:
    @staticmethod
    def create_request(sender, receivers, request_type, data=None, message=None):
        # Prevent duplicates
        if UserRequest.objects.filter(
            sender=sender,
            status=enums.UserRequestStatus.PENDING.value,
            request_type=request_type
        ).exists():
            return None, _("You already have a pending request!"), False

        # Create request
        user_request = UserRequest.objects.create(
            sender=sender,
            request_type=request_type,
            status=enums.UserRequestStatus.PENDING.value,
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

        return request_type, _("Request created successfully."), True

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
