"""
Centralized access point for cross-app models.
Use this ONLY outside of app-level models.py to avoid circular imports.
"""

from apps.user.models import User, UserRequest, WorkPlace, Sportsman, Trainer
from apps.sport.models import Tournament, Result, Sport
from apps.federation.models import Federation
from apps.education.models import School

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
