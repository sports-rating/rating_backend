import typing as t
import uuid
import random
import string
import requests

# django related
from django.conf import settings

# custom
from apps.shared.utils.logging import logger
from apps.shared.utils.redis_utils import get_redis_connection

redis_connection = get_redis_connection()


STATIC_CODE = "171717"
PHONE_NUMBER_WHITELIST = [
    settings.SUPER_ADMIN_PHONE_NUMBER, # super_admin
    "+998901234567", # Example Sportsman
    "+998901234568", # Example Trainer
    "+998901234569", # Example Federation
    "+998771112233",
    "+998935321377",
    "+998990054321",
    "+998998577232",
    "+998991234567", # user_f_1
    "+998991234568", # user_f_2 or trainer_2
    "+998991234569", # sportsman_1
    "+998991234570" # trainer_1
]


def generate_verification_code() -> str:
    # return "000000"
    return "".join(random.choices(string.digits, k=settings.VERIFICATION_CODE_LENGTH))


def send_verification_code(phone_number: str) -> tuple[int, str, t.Optional[str]]:
    verification_code = None
    error_status, error_text, verification_code_key, verified_phone_number_key = (
        check_existence_of_verification(phone_number)
    )

    if error_status:
        return error_status, error_text

    if phone_number in PHONE_NUMBER_WHITELIST:
        verification_code = STATIC_CODE
    else:
        verification_code = generate_verification_code()
        print(f"Generated verification code: {verification_code}")
        response = send_sms_message(
            phone_number,
            settings.VERIFICATION_CODE_MESSAGE_TEMPLATE.format(
                verification_code=verification_code
            ),
        )
        if response != 200:
            return 400, "Something went wrong with sending sms"

    # If sms sent successfuly, then we put it on redis
    redis_connection.set(
        verification_code_key, verification_code, ex=settings.VERIFICATION_CODE_EXPIRE
    )
    redis_connection.set(
        verified_phone_number_key,
        verification_code,
        ex=settings.VERIFICATION_CODE_EXPIRE,
    )

    return 200, "Verification code is successfully sent", verification_code


def check_existence_of_verification(
    phone_number: str,
) -> tuple[t.Optional[int], t.Optional[str], t.Optional[str], t.Optional[str]]:
    """Check whether if code has already been sent or number is already verified
    before sending verification code again. Prevents flood.
    """
    verification_code_key = f"verification_code:{phone_number}"
    verified_phone_number_key = f"verified_phone_number:{phone_number}"

    if redis_connection.get(verification_code_key):
        return 400, "Verification code already exist", None, None

    # if redis_connection.get(verified_phone_number_key):
    #     return 400, "Phone number already verified", None, None

    return None, None, verification_code_key, verified_phone_number_key


def send_sms_message(phone_number: str, text: str) -> int:
    response = requests.post(
        settings.PLAY_MOBILE_URL,
        json=create_sms_payload(phone_number, text),
        auth=(settings.PLAY_MOBILE_LOGIN, settings.PLAY_MOBILE_PASSWORD),
    )

    if response.status_code != 200:
        logger.error(f"Error on send_sms: {response.status_code=} {response.text=}")

    return response.status_code


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


def check_verification_status(phone_number: str) -> tuple[bool, str]:
    verification_status = redis_connection.get(f"verified_phone_number:{phone_number}")

    if verification_status is None:
        return False, "User must be verified first"

    if verification_status != "verified":
        return False, "Your phone number is not verified"

    return True, str()


def verify_code(phone_number: str, code: str):
    if not phone_number:
        return 400, "Send phone number to check verification"

    verification_code_key = f"verification_code:{phone_number}"
    stored_code = redis_connection.get(verification_code_key)
    # logger.info(f"Verification code: {redis_connection.get(verification_code_key)}")

    if stored_code is None:
        return 400, "Verification code expired or not found"

    if code != stored_code:
        return 400, "Verification code is incorrect"

    redis_connection.set(
        f"verified_phone_number:{phone_number}",
        "verified",
        ex=settings.VERIFICATION_CODE_EXPIRE,
    )
    redis_connection.unlink(
        verification_code_key
    )  # it won't be used, we don't have wait until it expires,
    # will be removed asynchronously

    return 200, "Verified successfully"
