from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    FileExtensionValidator
)

from rest_framework.exceptions import ValidationError

from apps import payment
from apps.shared.models import BaseModel
from apps.shared.utils import enums


class Transaction(BaseModel):
    """
    Model to store payment transactions.
    """
    CREATED = 0
    INITIATING = 1
    SUCCESSFULLY = 2
    CANCELED = -2
    CANCELED_DURING_INIT = -1

    STATE = [
        (CREATED, "Created"),
        (INITIATING, "Initiating"),
        (SUCCESSFULLY, "Successfully"),
        (CANCELED, "Canceled after successful performed"),
        (CANCELED_DURING_INIT, "Canceled during initiation"),
    ]

    user = models.ForeignKey(
        "user.User", on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_id = models.CharField(max_length=250)
    transaction_type = models.CharField(
        max_length=50,
        choices=enums.TransactionTypes.choices(),
    )
    status = models.CharField(
        max_length=50,
        choices=enums.TransactionStatus.choices(),
        default=enums.TransactionStatus.DRAFT.value
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    cancel_reason = models.TextField(null=True, blank=True)
    payment_details = models.JSONField(default=dict)
    payment_method = models.CharField(
        max_length=20,
        choices=enums.ProviderTypes.choices(),
        default=enums.ProviderTypes.PAYME.value
    )
    performed_time = models.DateTimeField(null=True, blank=True, db_index=True)
    cancelled_time = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "transaction"
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-created_time']
        indexes = [
            models.Index(fields=['transaction_id', "status", "payment_method"])
        ]

    repr_fields = ("user", "transaction_id", "status")
