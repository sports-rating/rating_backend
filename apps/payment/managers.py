import typing as t
from datetime import timedelta

from django.db import models
from django.db.models import Count, Q, Sum, Value, Model, QuerySet
from django.db.models.functions import Coalesce, TruncMonth
from django.conf import settings
from django.utils import timezone

from apps.shared.utils import enums

if t.TYPE_CHECKING:
    from apps.user.models import User
    from apps.payment.models import Transaction


class TransactionManager(models.Manager):
    def get_monthly_revenue(self):
        """
        Get the monthly revenue for successful transactions.
        """
        now = timezone.now()
        return (
            Transaction.objects.filter(
                status=enums.TransactionStatus.COMMITTED.value,  # or payme_state=Transaction.SUCCESSFULLY
                performed_time__year=now.year,
                performed_time__month=now.month,
            )
            .aggregate(total_revenue=Sum("amount"))["total_revenue"]
            or 0
        )

    def get_last_6_months_revenue(self):
        """
        Get the revenue for the last 6 months.
        """
        now = timezone.now()
        six_months_ago = now - timedelta(days=30 * 6)

        qs = (
            Transaction.objects.filter(
                status=enums.TransactionStatus.SUCCESS.value,
                performed_time__gte=six_months_ago,
            )
            .annotate(month=TruncMonth("performed_time"))
            .values("month")
            .annotate(total_revenue=Sum("amount"))
            .order_by("month")
        )

        # Format output for charts
        result = [
            {
                "month": month_data["month"].strftime("%b"),  # e.g. "Jan", "Feb"
                "total_revenue": float(month_data["total_revenue"] or 0)
            }
            for month_data in qs
        ]
        return result

    def get_yearly_revenue(self):
        """
        Get the yearly revenue for successful transactions.
        """
        now = timezone.now()

        qs = (
            Transaction.objects.filter(
                status=enums.TransactionStatus.SUCCESS.value,
                performed_time__year=now.year,
            )
            .annotate(month=TruncMonth("performed_time"))
            .values("month")
            .annotate(total_revenue=Sum("amount"))
            .order_by("month")
        )

        result = [
            {
                "month": month_data["month"].strftime("%b"),
                "total_revenue": float(month_data["total_revenue"] or 0)
            }
            for month_data in qs
        ]
        return result
