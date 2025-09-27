"""
Centralized access point for cross-app models.
Use this ONLY outside of app-level models.py to avoid circular imports.
"""

from apps.user.models import User, UserRequest, Sportsman, Trainer
from apps.sport.models import Tournament, Result, Sport, School
from apps.federation.models import Federation
from apps.career.models import WorkPlace, Education

__all__ = [
    "User",
    "Sportsman",
    "Trainer",
    "UserRequest",
    "WorkPlace",
    "Tournament",
    "Result",
    "Sport",
    "Federation",
    "School",
]
