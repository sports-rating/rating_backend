import typing as t
import math

from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.db.models import Count, Q, Sum, Value, Model, QuerySet
from django.db.models.functions import Coalesce, TruncMonth, TruncDay
from django.conf import settings
from django.utils import timezone

from dateutil.relativedelta import relativedelta
from datetime import timedelta
from collections import defaultdict


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

    def get_today_users(self) -> int:
        """
        Get today's unique visitors from Redis HyperLogLog.
        """
        from apps.shared.utils.redis_utils import (
            get_unique_visitors
        )

        today_str = timezone.now().date().strftime("%Y-%m-%d")
        today_users = get_unique_visitors(today_str)
        return today_users

    def get_last_6_months_user_growth(self) -> t.List[dict[str, t.Any]]:
        """
        Get the user growth for the last 6 months.
        """
        from apps.user.models import User
        now = timezone.now()
        six_months_ago = now - relativedelta(months=5)

        qs = (
            User.objects.filter(created_time__gte=six_months_ago)
            .annotate(month=TruncMonth("created_time"))
            .values("month")
            .annotate(total_users=Count("id"))
            .order_by("month")
        )

        monthly_data = {
            (item["month"].year, item["month"].month): item["total_users"]
            for item in qs
        }

        result = []
        for i in range(6):
            month_date = (now - relativedelta(months=5-i)).replace(day=1)
            key = (month_date.year, month_date.month)
            result.append({
                "month": month_date.strftime("%b"),
                "total_users": monthly_data.get(key, 0),
            })

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

    def get_detailed_statistics(self) -> dict[str, t.Any]:
        """
        Get detailed statistics for users.
        Includes:
        - Last 6 months growth
        - Yearly growth
        - Daily registrations (last 30 days)
        - Average daily registrations
        """
        from apps.user.models import User, DailyUsers
        from apps.shared.utils.redis_utils import (
            get_unique_visitors,
            get_unique_authenticated_users,
        )

        data = defaultdict(dict)

        # Last 6 months growth
        data["last_6_months_growth"] = self.get_last_6_months_user_growth()

        # Yearly growth
        data["yearly_growth"] = self.get_yearly_user_growth()

        # Daily registrations in the last 30 days
        now = timezone.now()
        one_month_ago = now - timedelta(days=30)

        daily_registrations = (
            User.objects.filter(created_time__gte=one_month_ago)
            .annotate(day=TruncDay("created_time"))
            .values("day")
            .annotate(total_users=Count("id"))
            .order_by("day")
        )

        daily_registrations_dict = {
            d["day"].date(): d for d in daily_registrations
        }

        # Building full list of days in the last 30 days
        days = [one_month_ago.date() + timedelta(days=i) for i in range(31)]

        # Convert to list of {day, total_users}
        daily_data = [
            {
                "day": day.strftime("%Y-%m-%d"),
                "total_users": daily_registrations_dict.get(day, {}).get("total_users", 0),
            }
            for day in sorted(days)
        ]
        data["daily_registrations_last_month"] = daily_data

        # Calculate average daily registration (for last 30 days)
        total_registered = sum(d["total_users"] for d in daily_data)
        active_days = len(daily_data) if daily_data else 1  # prevent division by zero
        average_daily = math.floor(total_registered / active_days)

        data["average_daily_registration"] = average_daily

        # Daily users from DailyUsers model
        daily_users_qs = DailyUsers.objects.filter(date__gte=one_month_ago).order_by("date")

        daily_users_dict = {
            d.date: d for d in daily_users_qs
        }

        daily_users_data = []
        for day in sorted(days):
            obj = daily_users_dict.get(day)
            daily_users_data.append({
                "day": day.strftime("%Y-%m-%d"),
                "total_users": obj.unique_users if obj else 0,
                "total_authenticated_users": obj.unique_authenticated_users if obj else 0,
            })
        data["daily_users_last_month"] = daily_users_data

        # Daily users average
        total_daily_users = sum(d["total_users"] for d in daily_users_data)
        average_daily_users = math.floor(total_daily_users / (len(daily_users_data) if daily_users_data else 1))
        data["average_daily_users"] = average_daily_users

        # Today's users
        today_str = now.date().strftime("%Y-%m-%d")
        today_users = get_unique_visitors(today_str)
        data["today_users"] = today_users

        return data


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
                cancelled=Count("id", filter=Q(status=enums.UserRequestStatus.CANCELLED.value)),
                total=Count("id"),
            )
        )

        stats = {}
        for request_type in enums.UserRequestTypes.choices():
            stats[request_type[0]] = {
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "cancelled": 0,
                "total": 0,
            }

        for row in qs:
            stats[row["request_type"]] = {
                "pending": row["pending"],
                "approved": row["approved"],
                "rejected": row["rejected"],
                "cancelled": row["cancelled"],
                "total": row["total"],
            }

        return stats
