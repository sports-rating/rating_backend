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
from django.core.exceptions import ValidationError

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
from apps.shared.services.payme.utils import time_to_payme, time_to_service

from apps.shared.utils.utils import (
    success_response,
    error_response
)

from apps.payment.models import (
    Transaction
)
from apps.user.models import User

from apps.payment.serializers import (
    CheckoutSerializer
)
from apps.shared.utils import enums

from apps.shared.services.payme import payme

RESULT_REQUEST_AMOUNT = settings.RESULT_REQUEST_AMOUNT


class CreateCheckoutAPIView(generics.GenericAPIView):
    """
    API endpoint for creating a checkout url
    """
    serializer_class = CheckoutSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: User = request.user
        payment_method: str = t.cast(str, serializer.validated_data.get("payment_method"))
        logger.info(f"Payment method: {payment_method}")

        transaction: Transaction = Transaction.objects.create(
            user=user,
            transaction_type=enums.TransactionTypes.RESULT_REQUEST.value,
            status=enums.TransactionStatus.DRAFT.value,
            payment_method=payment_method,
            amount=RESULT_REQUEST_AMOUNT
        )

        if payment_method == "payme":
            payment_link = payme.generate_payment_link(
                id=transaction.id,
                amount=transaction.amount
            )

        return success_response(
            message=_("Successfully created payment link"),
            data={
                "payment_link": payment_link,
                "transaction_id": transaction.id
            },
            code=status.HTTP_201_CREATED
        )


class PaymeWebhookAPIView(APIView):
    """
    A webhook view for Payme.
    """
    authentication_classes = []
    permission_classes = (permissions.AllowAny,)

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
        logger.info(f"Received Payme webhook!")  # LOGGING
        self.check_authorize(request)

        payme_methods = {
            "CheckPerformTransaction": self.check_perform_transaction,
            "CreateTransaction": self.create_transaction,
            "PerformTransaction": self.perform_transaction,
            "CancelTransaction": self.cancel_transaction,
            "CheckTransaction": self.check_transaction,
            "GetStatement": self.get_statement,
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
            logger.info(f"Payme method {method} processed with result: {result}")  # LOGGING
            return Response(result)

        raise exceptions.MethodNotFound("Method not supported yet!")

    def check_authorize(self, request: Request) -> None:
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

        if settings.PAYME_IS_TEST_MODE:
            if payme_key != settings.PAYME_TEST_KEY:
                raise exceptions.PermissionDenied("Invalid merchant key specified")
        elif payme_key != settings.PAYME_KEY:
            raise exceptions.PermissionDenied("Invalid merchant key specified")

    @exceptions.handle_exceptions
    def fetch_account(self, params: dict):
        """
        Fetch account based on settings and params.
        """
        internal_transaction_id = params["account"].get(settings.PAYME_ACCOUNT_FIELD)
        if not internal_transaction_id:
            raise exceptions.InvalidAccount("Missing account field in parameters.")

        internal_transaction = Transaction.objects.get(pk=internal_transaction_id)

        return internal_transaction

    @exceptions.handle_exceptions
    def validate_amount(self, internal_transaction, received_amount):
        """
        Validates if the amount matches for one-time payment accounts.
        paid_amount is received_amount and vice-versa
        """
        if not settings.PAYME_ONE_TIME_PAYMENT:
            return True

        expected_amount = Decimal(getattr(internal_transaction, settings.PAYME_AMOUNT_FIELD)) * 100
        received_amount = Decimal(received_amount)
        logger.info(f"Expected amount: {expected_amount}, Received amount: {received_amount}")  # LOGGING
        if expected_amount != received_amount:
            raise exceptions.IncorrectAmount(
                f"Invalid amount. Expected: {expected_amount}, received: {received_amount}"
            )

        return True

    @exceptions.handle_exceptions
    def check_perform_transaction(self, params: dict) -> response.CheckPerformTransaction:
        """
        Handle pre_create_transaction action.
        """
        logger.info(f"CHECK PERFORM Params: {params}")  # LOGGING
        internal_transaction = self.fetch_account(params)

        self.validate_amount(internal_transaction, params.get("amount", 0))

        result = response.CheckPerformTransaction(allow=True)
        return result.as_resp()

    @exceptions.handle_exceptions
    def create_transaction(self, params: dict) -> response.CreateTransaction:
        """
        Handle the create_transaction action.
        """
        # TODO CoderB7: Change account related fields and queryset
        logger.info(f"CREATE TRANSACTION Params: {params}")  # LOGGING
        external_transaction_id = params["id"]
        received_amount = Decimal(params.get("amount", 0))
        draft_tx = self.fetch_account(params)
        # logger.info(f"Draft Transaction: {draft_tx}")  # LOGGING

        self.validate_amount(draft_tx, received_amount)

        tx: None = None

        # Check if transaction already exists
        existing_tx = Transaction.objects.filter(transaction_id=external_transaction_id).first()
        if existing_tx:
            logger.info(f"Transaction {external_transaction_id} already exists (Payme).")
            result = response.CreateTransaction(
                transaction=existing_tx.transaction_id,
                state=existing_tx.payme_state,
                create_time=time_to_payme(existing_tx.created_time),
            ).as_resp()
            # logger.info(f"Transaction already exists: {result}")  # LOGGING
            return result

        # Handle draft logic
        if settings.PAYME_ONE_TIME_PAYMENT:
            if draft_tx.transaction_id and draft_tx.transaction_id != external_transaction_id:
                message = f"Transaction {draft_tx.transaction_id} already exists (Payme)."
                logger.warning(message)
                raise exceptions.TransactionAlreadyExists(message)

            # If draft has no Payme ID yet → update it
            if not draft_tx.transaction_id:
                logger.info(f"Updating draft transaction {draft_tx.id} with Payme ID {external_transaction_id}.")
                draft_tx.transaction_id = external_transaction_id
                draft_tx.status = enums.TransactionStatus.INITIATING.value
                draft_tx.payme_state = Transaction.INITIATING
                draft_tx.save(update_fields=["transaction_id", "amount", "payme_state", "status"])

                tx = draft_tx
            else:
                tx = draft_tx
        else:
            # Create fresh transaction
            tx = Transaction.objects.create(
                transaction_id=external_transaction_id,
                amount=received_amount / 100,
                account_id=draft_tx.pk,
                payme_state=Transaction.INITIATING,
            )

        result = response.CreateTransaction(
            transaction=tx.transaction_id,
            state=tx.payme_state,
            create_time=time_to_payme(tx.created_time),
        )
        result = result.as_resp()

        # callback event
        self.handle_created_payment(params, result)
        # logger.info(f"Transaction created: {result}")  # LOGGING
        return result

    @exceptions.handle_exceptions
    def perform_transaction(self, params: dict) -> response.PerformTransaction:
        """
        Handle the successful payment.
        """
        internal_transaction = Transaction.objects.filter(transaction_id=params["id"]).first()

        if internal_transaction.is_performed():
            result = response.PerformTransaction(
                transaction=internal_transaction.transaction_id,
                state=internal_transaction.payme_state,
                perform_time=time_to_payme(internal_transaction.performed_time),
            ).as_resp()
            logger.info(f"Transaction already performed: {result}")  # LOGGING
            return result

        internal_transaction.mark_as_performed()

        # Mark user profile is_result_paid = True
        user = internal_transaction.user
        if user and user.sportsman_profile:
            user.sportsman_profile.is_result_paid = True
            user.sportsman_profile.save(update_fields=["is_result_paid"])

        result = response.PerformTransaction(
            transaction=internal_transaction.transaction_id,
            state=internal_transaction.payme_state,
            perform_time=time_to_payme(internal_transaction.performed_time),
        )
        result = result.as_resp()

        # callback successful payment
        self.handle_successful_payment(params, result)
        # logger.info(f"Payment successful: {result}")  # LOGGING
        return result

    @exceptions.handle_exceptions
    def cancel_transaction(self, params) -> response.CancelTransaction:
        """
        Handle the cancelled payment.
        """
        internal_transaction = Transaction.objects.filter(transaction_id=params["id"]).first()

        if internal_transaction.is_cancelled():
            result = response.CancelTransaction(
                transaction=internal_transaction.transaction_id,
                state=internal_transaction.payme_state,
                cancel_time=time_to_payme(internal_transaction.cancelled_time)
            )
            return result.as_resp()

        if internal_transaction.is_performed():
            internal_transaction.mark_as_cancelled(
                cancel_reason=params["reason"],
                state=Transaction.CANCELLED
            )
        elif internal_transaction.is_created_in_payme():
            internal_transaction.mark_as_cancelled(
                cancel_reason=params["reason"],
                state=Transaction.CANCELLED_DURING_INIT
            )

        # Mark user profile is_result_paid = False, because of cancellation
        user = internal_transaction.user
        if user and user.sportsman_profile:
            user.sportsman_profile.is_result_paid = False
            user.sportsman_profile.save(update_fields=["is_result_paid"])

        result = response.CancelTransaction(
            transaction=internal_transaction.transaction_id,
            state=internal_transaction.payme_state,
            cancel_time=time_to_payme(internal_transaction.cancelled_time)
        )

        self.handle_cancelled_payment(params, result)

        return result.as_resp()

    @exceptions.handle_exceptions
    def check_transaction(self, params: dict) -> response.CheckTransaction:
        """
        Handle check transaction request.
        """
        internal_transaction = Transaction.objects.filter(transaction_id=params["id"]).first()

        result = response.CheckTransaction(
            transaction=internal_transaction.transaction_id,
            state=internal_transaction.payme_state,
            reason=internal_transaction.cancel_reason,
            create_time=time_to_payme(internal_transaction.created_time),
            perform_time=time_to_payme(internal_transaction.performed_time),
            cancel_time=time_to_payme(internal_transaction.cancelled_time),
        )

        return result.as_resp()

    @exceptions.handle_exceptions
    def get_statement(self, params: dict) -> response.GetStatement:
        """
        Retrieves a statement of transactions.
        """
        date_range = [time_to_service(params['from']), time_to_service(params['to'])]

        internal_transactions = Transaction.objects.filter(
            created_time__range=date_range
        ).order_by('-created_time')

        result = response.GetStatement(transactions=[])

        for transaction in internal_transactions:
            logger.info(f"transaction_id: {transaction.transaction_id}")  # LOGGING
            result.transactions.append({
                "transaction": transaction.transaction_id,
                "amount": int(transaction.amount * 100),
                "account": {
                    settings.PAYME_ACCOUNT_FIELD: transaction.id
                },
                "reason": transaction.cancel_reason,
                "state": transaction.payme_state,
                "created_time": time_to_payme(transaction.created_time),
                "perform_time": time_to_payme(transaction.performed_time),
                "cancel_time": time_to_payme(transaction.cancelled_time),
            })

        return result.as_resp()

    @exceptions.handle_exceptions
    def set_fiscal_data(self, params: dict) -> response.SetFiscalData:
        """
        Set fiscal data for the given transaction.
        """
        internal_transaction = Transaction.objects.filter(transaction_id=params["id"]).first()

        fiscal_data = params.get("fiscal_data")
        if not fiscal_data:
            raise exceptions.InvalidFiscalParams(
                "Missing fiscal_data field in parameters."
            )

        fiscal_type = params.get("type")
        if not fiscal_type:
            raise exceptions.InvalidFiscalParams(
                f"Invalid fiscal type. Expected 'PERFORM' or 'CANCEL', got: {fiscal_type}"
            )

        fiscal_data["type"] = fiscal_type
        internal_transaction.payment_details = fiscal_data
        internal_transaction.save()

        result = response.SetFiscalData(success=True)
        return result.as_resp()

    def handle_pre_payment(self, params, result, *args, **kwargs):
        """
        Handle the pre_create_transaction action. You can override this method
        """
        print(f"Transaction pre_created for this params: {params} and pre_created_result: {result}")

    def handle_created_payment(self, params, result, *args, **kwargs):
        """
        Handle the successful payment. You can override this method
        """
        print(f"Transaction created for this params: {params} and cr_result: {result}")

    def handle_successful_payment(self, params, result, *args, **kwargs):
        """
        Handle the successful payment. You can override this method
        """
        print(f"Payment successful for this params: {params} and result: {result}")

    def handle_cancelled_payment(self, params, result, *args, **kwargs):
        """
        Handle the cancelled payment. You can override this method
        """
        print(f"Payment cancelled for this params: {params} and result: {result}")
