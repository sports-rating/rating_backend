import typing as t

from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.db.models import Count, Q, Sum, Value, Model, QuerySet
from django.db.models.functions import Coalesce, TruncMonth
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


if t.TYPE_CHECKING:
    from apps.user.models import User


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The username must be set")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)

        extra_fields.setdefault("first_name", "Admin_B")
        extra_fields.setdefault("last_name", "Admin_B")
        extra_fields.setdefault("user_role", "super_admin")
        extra_fields.setdefault("phone_number", settings.SUPER_ADMIN_PHONE_NUMBER)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if extra_fields.get("user_role") != "super_admin":
            raise ValueError("Superuser must have role of super_admin.")

        return self.create_user(username, password, **extra_fields)


class UserStatisticsManager(models.Manager):

    def get_total_users(self) -> int:
        """
        Get the total number of users by role.
        """
        return self.get_queryset().aggregate(
            total_users=Count('id'),
            total_sportsmen=Count('id', filter=Q(user_role='sportsman')),
            total_trainers=Count('id', filter=Q(user_role='trainer')),
            total_sport_institution_admins=Count('id', filter=Q(user_role='sport_institution_admin')),
            total_federation_admins=Count('id', filter=Q(user_role='federation')),
            total_admins=Count('id', filter=Q(user_role='admin')),
        )

    def get_last_6_months_user_growth(self) -> t.List[dict[str, t.Any]]:
        """
        Get the user growth for the last 6 months.
        """
        from apps.user.models import User
        now = timezone.now()
        six_months_ago = now - timedelta(days=30 * 6)

        qs = (
            User.objects.filter(created_time__gte=six_months_ago)
            .annotate(month=TruncMonth("created_time"))
            .values("month")
            .annotate(total_users=Count("id"))
            .order_by("month")
        )

        result = [
            {
                "month": month_data["month"].strftime("%b"),  # e.g. Jan, Feb
                "total_users": month_data["total_users"],
            }
            for month_data in qs
        ]
        return result

    def get_yearly_user_growth(self) -> t.List[dict[str, t.Any]]:
        """
        Get the user growth for the current year.
        """
        from apps.user.models import User
        now = timezone.now()

        qs = (
            User.objects.filter(created_time__year=now.year)
            .annotate(month=TruncMonth("created_time"))
            .values("month")
            .annotate(total_users=Count("id"))
            .order_by("month")
        )

        result = [
            {
                "month": month_data["month"].strftime("%b"),
                "total_users": month_data["total_users"],
            }
            for month_data in qs
        ]
        return result


    def get_sportsman_statistics(self, user: "User") -> dict[str, int]:
        """
        Calculate statistics for a sportsman based on their results.
        """
        # Aggregate counts directly in the database
        return user.results.aggregate(
            total_gold=Count('id', filter=Q(rating=1)),
            total_silver=Count('id', filter=Q(rating=2)),
            total_bronze=Count('id', filter=Q(rating=3)),
            total_competitions=Count('id', distinct=True)
        )

    def with_sportsman_statistics(self) -> QuerySet[Model]:
        """
        Annotate the queryset with sportsman statistics.
        """
        return self.get_queryset().annotate(
            total_gold=Count('results', filter=Q(results__rating=1), distinct=True),
            total_silver=Count('results', filter=Q(results__rating=2), distinct=True),
            total_bronze=Count('results', filter=Q(results__rating=3), distinct=True),
            total_competitions=Count('results', distinct=True)
        )

    def with_trainer_statistics(self) -> QuerySet[Model]:
        """
        Annotate the queryset with trainer statistics
        """
        # Aggregate both trainer's own achievements and students' achievements in a single query
        queryset = self.get_queryset().annotate(
            # Trainer's own results (current participation)
            own_total_gold=Coalesce(
                Count('results', filter=Q(results__currently_participating=True, results__rating=1)),
                Value(0)
            ),
            own_total_silver=Coalesce(
                Count('results', filter=Q(results__currently_participating=True, results__rating=2)),
                Value(0)
            ),
            own_total_bronze=Coalesce(
                Count('results', filter=Q(results__currently_participating=True, results__rating=3)),
                Value(0)
            ),

            # Students' aggregated results (when not currently participating)
            students_total_gold=Coalesce(
                Sum('results__gold', filter=Q(results__currently_participating=False)),
                Value(0)
            ),
            students_total_silver=Coalesce(
                Sum('results__silver', filter=Q(results__currently_participating=False)),
                Value(0)
            ),
            students_total_bronze=Coalesce(
                Sum('results__bronze', filter=Q(results__currently_participating=False)),
                Value(0)
            ),
        )

        return queryset

    def get_trainer_statistics(self, user: "User") -> dict[str, dict[str, int]]:
        """
        Calculate statistics for a trainer based on their results and their students' results.
        """
        # Aggregate both trainer's own achievements and students' achievements in a single query
        statistics = user.results.aggregate(
            own_total_gold=Coalesce(Count('id', filter=Q(currently_participating=True, rating=1)), Value(0)),
            own_total_silver=Coalesce(Count('id', filter=Q(currently_participating=True, rating=2)), Value(0)),
            own_total_bronze=Coalesce(Count('id', filter=Q(currently_participating=True, rating=3)), Value(0)),
            students_total_gold=Coalesce(Sum('gold', filter=Q(currently_participating=False)), Value(0)),
            students_total_silver=Coalesce(Sum('silver', filter=Q(currently_participating=False)), Value(0)),
            students_total_bronze=Coalesce(Sum('bronze', filter=Q(currently_participating=False)), Value(0)),
        )

        # Combine all statistics
        total_statistics = {
            "gold": statistics["own_total_gold"] + statistics["students_total_gold"],
            "silver": statistics["own_total_silver"] + statistics["students_total_silver"],
            "bronze": statistics["own_total_bronze"] + statistics["students_total_bronze"],
        }

        return {
            "own_statistics": {
                "gold": statistics["own_total_gold"],
                "silver": statistics["own_total_silver"],
                "bronze": statistics["own_total_bronze"],
            },
            "students_statistics": {
                "gold": statistics["students_total_gold"],
                "silver": statistics["students_total_silver"],
                "bronze": statistics["students_total_bronze"],
            },
            "total_statistics": total_statistics,
        }


class UserRequestStatisticsManager(models.Manager):

    def get_request_statistics(self) -> dict[str, t.Any]:
        from apps.user.models import UserRequest
        from apps.shared.utils import enums

        qs = (
            UserRequest.objects.values("request_type")
            .annotate(
                pending=Count("id", filter=Q(status=enums.UserRequestStatus.PENDING.value)),
                approved=Count("id", filter=Q(status=enums.UserRequestStatus.ACCEPTED.value)),
                rejected=Count("id", filter=Q(status=enums.UserRequestStatus.REJECTED.value)),
                total=Count("id"),
            )
        )

        stats = {}
        for row in qs:
            stats[row["request_type"]] = {
                "pending": row["pending"],
                "approved": row["approved"],
                "rejected": row["rejected"],
                "total": row["total"],
            }

        return stats
