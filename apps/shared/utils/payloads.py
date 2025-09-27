import uuid
from django.conf import settings


TRAINER_FEDERATION_ADMIN_APPROVAL_REQUIRED_FIELDS = [
    "full_name", "phone_number", "email", "birth_date"
]

SPORTSMAN_APPROVAL_REQUIRED_FIELDS = [
    "trainer", "sport", "height", "weight", "sport_rank"
]

TRAINER_APPROVAL_REQUIRED_FIELDS = [
    "federation", "sport", "skill_level", "division", "height", "weight"
]

SPORTSMAN_RESULT_APPROVAL_REQUIRED_FIELDS = [
    "trainer", "tournament", "country", "year", "currently_participating", "rating"
]

def create_sms_payload(phone_number: str, text: str) -> dict:
    return {
        "messages": [
            {
                "recipient": phone_number,
                "message-id": "7srating-{}".format(uuid.uuid4()),
                "sms": {
                    "originator": settings.PLAY_MOBILE_ORIGINATOR,
                    "content": {"text": text},
                },
            }
        ]
    }
