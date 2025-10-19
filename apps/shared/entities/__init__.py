"""
Centralized access point for cross-app models.
Use this ONLY outside of app-level models.py to avoid circular imports.
"""

from apps.user.models import User, UserRequest, Sportsman, Trainer, TemporaryFile
from apps.sport.models import Tournament, Sport, SportInstitution
from apps.federation.models import Federation
from apps.career.models import WorkPlace, Education, Result

__all__ = [
    "User",
    "Sportsman",
    "Trainer",
    "UserRequest",
    "TemporaryFile",
    "WorkPlace",
    "Tournament",
    "Result",
    "Sport",
    "Federation",
    "SportInstitution",
]
