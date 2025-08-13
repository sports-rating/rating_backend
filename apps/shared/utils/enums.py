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
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    ORDINARY = "ordinary"
    SPORTSMAN = "sportsman"
    TRAINER = "trainer"
    FEDERATION = "federation"


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
    CANCELLED = "cancelled"


class SportRankEnum(BaseEnum):
    YOUTH_3 = "Youth Third Rank"
    YOUTH_2 = "Youth Second Rank"
    YOUTH_1 = "Youth First Rank"
    ADULT_3 = "Adult Third Rank"
    ADULT_2 = "Adult Second Rank"
    ADULT_1 = "Adult First Rank"
    CANDIDATE = "Candidate for Master of Sport"
