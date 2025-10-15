import typing as t

from django.db import models
from django.db.models import Count, Q, Sum, Value, Model, QuerySet
from django.db.models.functions import Coalesce
from django.conf import settings


if t.TYPE_CHECKING:
    from apps.user.models import User
    from apps.federation.models import Federation


class FederationManager(models.Manager):
    def get_total_federations(self) -> int:
        """
        Get the total number of federations.
        """
        return self.get_queryset().count()
