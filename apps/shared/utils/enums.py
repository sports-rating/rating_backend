from enum import Enum
from typing import TypeVar


ModelType = TypeVar("ModelType")


class BaseEnum(Enum):
    @classmethod
    def choices(cls):
        return [(choice.value, choice.name) for choice in cls]


class SportsChoices(BaseEnum):
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    BASEBALL = "baseball"
    HOCKEY = "hockey"
    RUGBY = "rugby"
    VOLLEYBALL = "volleyball"
    CRICKET = "cricket"
    # INDIVIDUAL
    TENNIS = "tennis"
    GOLF = "golf"
    BOXING = "boxing"
    WRESTLING = "wrestling"
    MARTIAL_ARTS = "martial_arts"
    SWIMMING = "swimming"
    GYMNASTICS = "gymnastics"
    CYCLING = "cycling"
    # COMBAT 
    MMA = "MMA"
    KICKBOXING = "kickboxing"
    MUAY_THAI = "Muay Thai"
    JIU_JITSU = "JIU JITSU"


class GenderChoices(BaseEnum):
    MALE = "male"
    FEMALE = "female"


class MediaChoices(BaseEnum):
    IMAGE = "image"
    VIDEO = "video"
    PDF = "pdf"


class UserRoles(BaseEnum):
    ADMIN = "admin"
    ORDINARY = "ordinary"
    SPORTSMAN = "sportsman"
    TRAINER = "trainer"
    

class SchoolChoices(BaseEnum):
    ORDINARY = "ordinary"
    CLUB = "club"


class LanguageTypes(BaseEnum):
    EN = "en"
    RU = "ru"
    UZ = "uz"


class UserRequestTypes(BaseEnum):
    TRAINER_REQUEST = "trainer_request"
    FEDERATION_REQUEST = "federation_request"


class UserRequestStatus(BaseEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
