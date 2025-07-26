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
    device = FCMDevice.objects.filter(user_id=user_id).first()
    
    # Ensure all data values are string
    stringified_data = {str(k): str(v) for k, v in data.items()}

    if not device:
        logger.warning(f"No FCM device found for user {user_id}")
        return None
    
    # Create the notification message
    message = Message(
        notification=Notification(title=title, body=body),
        data=stringified_data,
        token=device.registration_id,
    )

    # Send the message
    try:
        response = device.send_message(message)
        logger.info(f"Notification sent to user {user_id}: {response}")
    except Exception as e:
        logger.error(f"Failed to send FCM notification to user {user_id}: {e}")
        return

    UserNotification.objects.create(
        user_id=user_id,
        title=title,
        text=body,
        request=user_request,
        data=stringified_data,
    )


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
    logger.info("Sending notification")
    send_firebase_notification(
        user_request=user_request,
        title=title,
        body=body,
        user_id=user.id,
        data=extra,
    )

    # implement logic of sending telegram message also

