import typing as t
import base64
import binascii

from uuid import UUID
from typing import reveal_type
from decimal import Decimal

from django.shortcuts import render
from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from django.http import HttpResponse
from django.db.models import Q, Prefetch, QuerySet
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.utils.module_loading import import_string

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import generics, permissions, status, filters as rest_framework_filters
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import BasePermission

from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.permissions import IsAdmin, IsAdminOrSuperAdmin
from apps.shared.utils.pagination import CustomPagination
from apps.shared.utils.logging import logger

from apps.shared.services.payme import exceptions
from apps.shared.services.payme import response
from apps.shared.services.payme.utils import time_to_payme

from apps.shared.utils.utils import (
    success_response,
    error_response
)

from apps.payment.models import (
    Transaction
)


class PaymeWebhookAPIView(APIView):
    """
    A webhook view for Payme.
    """

    def post(self, request, *args, **kwargs):
        """
        Handle the incoming webhook request.

        In the Payme webhook, the following fields are important:
        - external_transaction_id
        - received_amount

        Project's fields:
        - internal_transaction_id
        - expected_amount
        """
        self.check_authorize(request)

        payme_methods = {
            "GetStatement": self.get_statement,
            "CancelTransaction": self.cancel_transaction,
            "PerformTransaction": self.perform_transaction,
            "CreateTransaction": self.create_transaction,
            "CheckTransaction": self.check_transaction,
            "CheckPerformTransaction": self.check_perform_transaction,
            "SetFiscalData": self.set_fiscal_data,
        }

        try:
            method = request.data.get("method")
            params = request.data.get("params")
        except KeyError as exc:
            message = f"Error processing webhook: {exc}"
            raise exceptions.InternalServiceError(message) from exc

        if method in payme_methods:
            result = payme_methods[method](params)
            return Response(result)

        raise exceptions.MethodNotFound("Method not supported yet!")

    @staticmethod
    def check_authorize(request: Request) -> None:
        """
        Verify the integrity of the request using the merchant key.
        """
        password = request.META.get("HTTP_AUTHORIZATION")
        if not password:
            raise exceptions.PermissionDenied("Missing authentication credentials")

        password = password.split(" ")[1]

        try:
            password = base64.b64decode(password).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise exceptions.PermissionDenied("Decoding error in authentication credentials") from exc

        try:
            payme_key = password.split(':')[-1]
        except IndexError as exc:
            message = "Invalid merchant key format in authentication credentials"
            raise exceptions.PermissionDenied(message) from exc

        if payme_key != settings.PAYME_KEY:
            raise exceptions.PermissionDenied("Invalid merchant key specified")

    def fetch_account(self, params: dict):
        """
        Fetch account based on settings and params.
        """
        internal_transaction_id = params["account"].get(settings.PAYME_ACCOUNT_FIELD)
        if not internal_transaction_id:
            raise exceptions.InvalidAccount("Missing account field in parameters.")

        transaction = Transaction.objects.get(pk=internal_transaction_id)

        return transaction

    def validate_amount(self, internal_transaction, received_amount):
        """
        Validates if the amount matches for one-time payment accounts.
        paid_amount is received_amount and vice-versa
        """
        if not settings.PAYME_ONE_TIME_PAYMENT:
            return True

        expected_amount = Decimal(getattr(internal_transaction, settings.PAYME_AMOUNT_FIELD)) * 100
        received_amount = Decimal(received_amount)

        if expected_amount != received_amount:
            raise exceptions.IncorrectAmount(
                f"Invalid amount. Expected: {expected_amount}, received: {received_amount}"
            )

        return True

    def check_perform_transaction(self, params: dict) -> response.CheckPerformTransaction:
        """
        Handle pre_create_transaction action.
        """
        internal_transaction = self.fetch_account(params)
        self.validate_amount(internal_transaction, params.get("amount", 0))

        result = response.CheckPerformTransaction(allow=True)
        return result.as_resp()

    def create_transaction(self, params: dict) -> dict:
        """
        Handle the create_transaction action.
        """
        # TODO CoderB7: Change account related fields and queryset
        external_transaction_id = params.get("id")
        received_amount = Decimal(params.get("amount", 0))
        internal_transaction = self.fetch_account(params)

        self.validate_amount(internal_transaction, received_amount)

        defaults = {
            "amount": received_amount,
            "state": Transaction.INITIATING,
            "account_id": internal_transaction.pk,
        }

        if settings.PAYME_ONE_TIME_PAYMENT:
            # Check for an existing transaction with a different transaction_id for the given account
            if (
                Transaction.objects.filter(id=internal_transaction.pk)
                .exclude(transaction_id=external_transaction_id)
                .exists()
            ):
                message = f"Transaction {external_transaction_id} already exists (Payme)."
                logger.warning(message)
                raise exceptions.TransactionAlreadyExists(message)

        internal_transaction, _ = Transaction.objects.get_or_create(
            transaction_id=external_transaction_id,
            defaults=defaults
        )

        result = response.CreateTransaction(
            transaction=internal_transaction.transaction_id,
            state=internal_transaction.state,
            create_time=time_to_payme(internal_transaction.created_at),
        )
        result = result.as_resp()

        # callback event
        self.handle_created_payment(params, result)

        return result


    def handle_created_payment(self, params, result, *args, **kwargs):
        """
        Handle the successful payment. You can override this method
        """
        print(f"Transaction created for this params: {params} and cr_result: {result}")
