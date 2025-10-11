from enum import Enum
from typing import TypeVar


ModelType = TypeVar("ModelType")


class BaseEnum(Enum):
    @classmethod
    def choices(cls):
        return [(choice.value, choice.name) for choice in cls]

    @classmethod
    def values(cls):
        return [choice.value for choice in cls]


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
    SPORT_INSTITUTION_ADMIN = "sport_institution_admin"


class SportInstitutionChoices(BaseEnum):
    SPORT_SCHOOL = "sport_school"
    SPORT_CLUB = "sport_club"
    SPORT_COMPLEX = "sport_complex"


class SportInstitutionRequestStatus(BaseEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LanguageTypes(BaseEnum):
    EN = "en"
    RU = "ru"
    UZ = "uz"


class UserRequestTypes(BaseEnum):
    SPORTSMAN_TRAINER_REQUEST = "sportsman_trainer_request"
    TRAINER_FEDERATION_REQUEST = "trainer_federation_request"
    # SPORTSMAN_TO_TRAINER = "sportsman_to_trainer"
    # TRAINER_TO_FEDERATION = "trainer_to_federation"
    FEDERATION_ADMIN_REQUEST = "federation_admin_request"
    SPORTSMAN_RESULT_VERIFICATION_REQUEST = "sportsman_result_verification_request"
    TRAINER_WORKPLACE_VERIFICATION_REQUEST = "trainer_workplace_verification_request"
    EDUCATION_VERIFICATION_REQUEST = "education_verification_request"


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
    MASTER_OF_SPORT = "Master of Sport"


class ResultVerificationStatus(BaseEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ProviderTypes(BaseEnum):
    PAYME = "payme"
    CLICK = "click"
    UZUM = "uzum"


class TransactionStatus(BaseEnum):
    DRAFT = "draft"
    INITIATING = "initiating"
    COMMITTED = "committed"
    REFUNDED = "refunded"
    REJECTED = "rejected"
    # FAILED = "failed"
    CANCELED = "canceled"
    TIMEOUT = "timeout"


class TransactionTypes(BaseEnum):
    RESULT_REQUEST = "result_request"
    EDUCATION_REQUEST = "education_request"
    WORK_PLACE_REQUEST = "work_place_request"
    SUBSCRIPTION_SPORTSMAN = "subscription_sportsman"
    SUBSCRIPTION_TRAINER = "subscription_trainer"


class SectionTypes(BaseEnum):
    RESULT = "result"
    EDUCATION = "education"
    WORK_PLACE = "work_place"


class CurrencyTypes(BaseEnum):
    UZS = "UZS"
    USD = "USD"
    RUB = "RUB"
