from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    FileExtensionValidator
)
from django.utils import timezone

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
    CANCELLED = -2
    CANCELLED_DURING_INIT = -1

    PAYME_STATE = [
        (CREATED, "Created"),
        (INITIATING, "Initiating"),
        (SUCCESSFULLY, "Successfully"),
        (CANCELLED, "Canceled after successful performed"),
        (CANCELLED_DURING_INIT, "Canceled during initiation"),
    ]

    CLICK_STATE = [
        (CREATED, "Created"),
        (INITIATING, "Initiating"),
        (SUCCESSFULLY, "Successfully"),
        (CANCELLED, "Canceled after successful performed"),
    ]

    user = models.ForeignKey(
        "user.User", on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_id = models.CharField(max_length=250)
    transaction_type = models.CharField(
        max_length=50,
        choices=enums.TransactionTypes.choices(),
    )

    payme_state = models.IntegerField(choices=PAYME_STATE, default=CREATED)
    click_state = models.IntegerField(choices=CLICK_STATE, default=CREATED)

    status = models.CharField(
        max_length=50,
        choices=enums.TransactionStatus.choices(),
        default=enums.TransactionStatus.DRAFT.value
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    cancel_reason = models.IntegerField(null=True, blank=True)
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

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.status}"

    def is_performed(self) -> bool:
        """
        Check if the transaction is completed.

        :return: True if the transaction is completed, False otherwise.
        """
        return self.payme_state == self.SUCCESSFULLY

    def is_cancelled(self) -> bool:
        """
        Check if the transaction is cancelled.

        :return: True if the transaction is cancelled, False otherwise.
        """
        return self.payme_state in [
            self.CANCELLED,
            self.CANCELLED_DURING_INIT
        ]

    def is_created(self) -> bool:
        """
        Check if the transaction is created.

        :return: True if the transaction is created, False otherwise.
        """
        return self.payme_state == self.CREATED

    def is_created_in_payme(self) -> bool:
        """
        Check if the transaction was created in Payme.

        :return: True if the transaction was created in Payme, False otherwise.
        """
        return self.payme_state == self.INITIATING

    def mark_as_cancelled(self, cancel_reason: int, state: int) -> bool:
        """
        Mark the transaction as cancelled.

        :param cancel_reason: The reason for cancelling the transaction.
        :return: True if the transaction was successfully marked as cancelled, False otherwise.
        """
        if self.payme_state == state:
            return self

        self.payme_state = state
        self.status = enums.TransactionStatus.CANCELED.value
        self.cancel_reason = cancel_reason
        self.cancelled_time = timezone.now()
        self.save()
        return True

    def mark_as_performed(self) -> bool:
        """
        Mark the transaction as performed.

        :return: True if the transaction was successfully marked as performed, False otherwise.
        """
        if self.payme_state != self.INITIATING:
            return False

        self.payme_state = self.SUCCESSFULLY
        self.status = enums.TransactionStatus.COMMITTED.value
        self.performed_time = timezone.now()
        self.save()
        return True
