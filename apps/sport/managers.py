import typing as t

from django.db import models
from django.db.models import Count, Q, Sum, Value, Model, QuerySet
from django.db.models.functions import Coalesce
from django.conf import settings


if t.TYPE_CHECKING:
    from apps.user.models import User
    from apps.sport.models import Sport, SportInstitution


class SportManager(models.Manager):
    def get_total_sports(self) -> int:
        """
        Get the total number of sports.
        """
        return self.get_queryset().count()



class SportInstitutionManager(models.Manager):
    def get_total_sport_institutions(self) -> int:
        """
        Get the total number of sport institutions.
        """
        return self.get_queryset().count()
