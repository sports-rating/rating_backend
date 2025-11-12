import typing as t
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.db import models
from django.db.models import Count, Q, Sum, Value, Model, QuerySet, Case, When, F
from django.db.models.functions import Coalesce, TruncMonth, TruncDay
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
        from apps.payment.models import Transaction
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
        from apps.payment.models import Transaction
        now = timezone.now()
        six_months_ago = now - relativedelta(months=5)

        qs = (
            Transaction.objects.filter(
                status=enums.TransactionStatus.COMMITTED.value,
                performed_time__gte=six_months_ago.replace(day=1),
            )
            .annotate(month=TruncMonth("performed_time"))
            .values("month")
            .annotate(total_revenue=Coalesce(
                Sum("amount"),
                Value(0, output_field=models.DecimalField()))
            )
            .order_by("month")
        )

        monthly_data = {
            (item["month"].year, item["month"].month): float(item["total_revenue"] or 0)
            for item in qs
        }

        result = []
        for i in range(6):
            month_date = (now - relativedelta(months=5 - i)).replace(day=1)
            key = (month_date.year, month_date.month)
            result.append({
                "month": month_date.strftime("%b"),
                "total_revenue": monthly_data.get(key, 0.0),
            })
        return result

    def get_yearly_revenue(self):
        """
        Get the yearly revenue for successful transactions.
        """
        from apps.payment.models import Transaction
        now = timezone.now()

        qs = (
            Transaction.objects.filter(
                status=enums.TransactionStatus.COMMITTED.value,
                performed_time__year=now.year,
            )
            .annotate(month=TruncMonth("performed_time"))
            .values("month")
            .annotate(total_revenue=Sum("amount"))
            .order_by("month")
        )

        monthly_data = {q["month"].month: q["total_revenue"] or 0 for q in qs}

        result = []
        for m in range(1, 13):
            result.append({
                "month": timezone.datetime(now.year, m, 1).strftime("%b"),
                "total_revenue": float(monthly_data.get(m, 0))
            })
        return result

    def get_detailed_statistics(self) -> dict[str, t.Any]:
        """
        Get detailed statistics for transactions.
        """
        from apps.payment.models import Transaction
        from apps.federation.models import Federation
        from collections import defaultdict

        now = timezone.now()

        # Base queryset for successful transactions
        base_qs = Transaction.objects.filter(
            status=enums.TransactionStatus.COMMITTED.value
        )

        # Overall summary
        summary = base_qs.filter(
            performed_time__year=now.year,
        ).aggregate(
            total_revenue=Coalesce(
                Sum("amount"),
                Value(0, output_field=models.DecimalField()),
                output_field=models.DecimalField()
            ),
            total_transactions=Count("id"),
            total_revenue_month=Coalesce(
                Sum(
                    Case(
                        When(performed_time__month=now.month, then="amount"),
                        default=Value(0, output_field=models.DecimalField()),
                        output_field=models.DecimalField(),
                    ),
                    output_field=models.DecimalField(),
                ),
                Value(0, output_field=models.DecimalField()),
            ),
            total_transactions_month=Count(
                Case(When(performed_time__month=now.month, then=1))
            ),
        )

        data = {
            "total_revenue": float(summary["total_revenue"] or 0),
            "total_transactions": summary["total_transactions"],
            "total_revenue_month": float(summary["total_revenue_month"] or 0),
            "total_transactions_month": summary["total_transactions_month"],
            "yearly_revenue": self.get_yearly_revenue(),
        }

        # Daily revenue (last 31 days)
        one_month_ago = now - timedelta(days=30)
        daily_revenue_qs = (
            base_qs.filter(performed_time__gte=one_month_ago)
            .annotate(day=TruncDay("performed_time"))
            .values("day")
            .annotate(
                total_revenue=Coalesce(Sum("amount"), Value(0, output_field=models.DecimalField())),
                total_transactions=Count("id"),
            )
        )

        daily_revenue_dict = {
            d["day"].date(): d for d in daily_revenue_qs
        }

        # Bulding full list of days in the last 30 days
        days = [one_month_ago.date() + timedelta(days=i) for i in range (31)]

        data["daily_revenue_last_30_days"] = [
            {
                "day": day.strftime("%Y-%m-%d"),
                "total_revenue": float(daily_revenue_dict.get(day, {}).get("total_revenue", 0)),
                "total_transactions": daily_revenue_dict.get(day, {}).get("total_transactions", 0),
            }
            for day in sorted(days)
        ]

        # Breakdown by user role
        role_stats = (
            base_qs.filter(performed_time__year=now.year).values('user__user_role').annotate(
                revenue=Coalesce(
                    Sum("amount"),
                    Value(0, output_field=models.DecimalField()),
                    output_field=models.DecimalField()
                ),
                transactions=Count("id")
            )
        )

        user_roles = [
            enums.UserRoles.SPORTSMAN.value,
            enums.UserRoles.TRAINER.value,
            enums.UserRoles.SPORT_INSTITUTION_ADMIN.value,
            enums.UserRoles.FEDERATION.value,
        ]

        role_stats_dict = {
            user_role: {
                "revenue": next((r["revenue"] for r in role_stats if r["user__user_role"] == user_role), 0),
                "transactions": next((r["transactions"] for r in role_stats if r["user__user_role"] == user_role), 0),
            }
            for user_role in user_roles
        }
        data["by_user_role"] = role_stats_dict

        # Breakdown by payment method
        total_transactions = base_qs.filter(performed_time__year=now.year).count() or 1  # prevent division by zero

        payment_methods_stats = (
            base_qs.filter(performed_time__year=now.year).values("payment_method")
            .annotate(
                revenue=Coalesce(
                    Sum("amount"),
                    Value(0, output_field=models.DecimalField()),
                    output_field=models.DecimalField(),
                ),
                transactions=Count("id"),
            )
            .annotate(
                percentage=Coalesce(
                    (100.0 * F("transactions") / total_transactions),
                    Value(0, output_field=models.DecimalField()),
                    output_field=models.DecimalField(),
                )
            )
            .order_by("-percentage")
        )

        payment_methods_dict = {
            pm["payment_method"]: {
                "revenue": pm["revenue"],
                "transactions": pm["transactions"],
                "percentage": round(float(pm["percentage"] or 0), 1)
            }
            for pm in payment_methods_stats
        }
        data["by_payment_method"] = payment_methods_dict

        # Breakdown by federations
        # Sportsmen-related transactions
        sportsmen_stats = (
            base_qs.filter(user__sportsman_profile__trainer__federation__isnull=False)
            .values("user__sportsman_profile__trainer__federation__id", "user__sportsman_profile__trainer__federation__name")
            .annotate(
                revenue=Coalesce(Sum("amount"), Value(0, output_field=models.DecimalField())),
                transactions=Count("id"),
            )
        )

        # Trainer-related transactions
        trainer_stats = (
            base_qs.filter(user__trainer_profile__federation__isnull=False)
            .values("user__trainer_profile__federation__id", "user__trainer_profile__federation__name")
            .annotate(
                revenue=Coalesce(Sum("amount"), Value(0, output_field=models.DecimalField())),
                transactions=Count("id"),
            )
        )

        federation_data = defaultdict(lambda: {"revenue": 0, "transactions": 0})

        for row in sportsmen_stats:
            fid = row["user__sportsman_profile__trainer__federation__id"]
            federation_data[fid]["name"] = row["user__sportsman_profile__trainer__federation__name"]
            federation_data[fid]["revenue"] += row["revenue"]
            federation_data[fid]["transactions"] += row["transactions"]

        for row in trainer_stats:
            fid = row["user__trainer_profile__federation__id"]
            federation_data[fid]["name"] = row["user__trainer_profile__federation__name"]
            federation_data[fid]["revenue"] += row["revenue"]
            federation_data[fid]["transactions"] += row["transactions"]

        data["by_federation"] = {}

        for federation in Federation.objects.all():
            f_id = federation.id
            stat = federation_data.get(f_id, {"name": federation.name, "revenue": 0, "transactions": 0})
            data["by_federation"][stat["name"]] = {
                "revenue": stat["revenue"],
                "transactions": stat["transactions"],
            }

        return data
