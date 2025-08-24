import typing as t
import uuid

from django.db.models import Model

from rest_framework.request import Request

from apps.user.models import (
    User,
    Sportsman,
    Trainer
)
from apps.federation.models import Federation
from apps.sport.models import Sport

__all__ = (
    "UserT",
    "ModelT",
    "SportsmanT",
    "TrainerT",
    "FederationT",
    "SportT",
    "uuidT"
)

# Model Type variables
UserT = t.TypeVar('UserT', bound=User)
ModelT = t.TypeVar('ModelT', bound=Model)
SportsmanT = t.TypeVar('SportsmanT', bound=Sportsman)
TrainerT = t.TypeVar('TrainerT', bound=Trainer)
FederationT = t.TypeVar('FederationT', bound=Federation)
SportT = t.TypeVar('SportT', bound=Sport)

# Request Type variable
RequestT = t.TypeVar('RequestT', bound=Request)

uuidT = t.TypeVar('uuidT', bound=uuid.UUID)
