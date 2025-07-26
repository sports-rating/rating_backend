from firebase_admin.messaging import Message, Notification
from fcm_django.models import FCMDevice

from apps.shared.utils.logging import logger
from apps.user.models import UserNotification
from apps.user.models import User, UserRequest


def send_firebase_notification(
    user_request: UserRequest,
    title: str,
    body: str,
    user_id: str,
    data: dict = None,
) -> None:
    """
    Send a notification to a specific user using FCM.
    """
    if data is None:
        data = {}

    # Get the devices for the specified users
    device = FCMDevice.objects.filter(user_id=user_id)
    
    if not device.exists():
        return None
    
    # Create the notification message
    message = Message(
        notification=Notification(title=title, body=body),
        data=data,
        tokens=device.values_list("registration_id", flat=True),
    )

    # Send the message
    response = FCMDevice.send_message(message)
    logger.info(f"Notification sent to user {user_id}: {response}")

    notification = UserNotification(
        user_id=user_id,
        title=title,
        text=body,
        request=user_request,
        data=data
    )
    notification.save()


def send_notification_to_user(
        user: User, 
        user_request: UserRequest,
        title: str, 
        body: str, 
        **extra
    ) -> None:
    """
    Sends a notification to a specific user.
    """
    if not user:
        logger.info(f"User does not exists")
        return None
    
    send_firebase_notification(
        user_request=user_request,
        title=title,
        body=body,
        user_id=user.id,
        data=extra,
    )

    # implement logic of sending telegram message also

