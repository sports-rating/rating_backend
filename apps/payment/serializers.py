import typing as t

from uuid import UUID


from django.db import transaction, IntegrityError
from django.utils.translation import gettext as _
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings

from rest_framework import serializers

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.general import (
    get_file_full_url,
    check_uniqueness,
    check_m2m_uniqueness
)
from apps.shared.utils.mixins import RequestContextMixin
from apps.shared.utils import enums

from apps.payment.models import Transaction


class CheckoutSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=enums.ProviderTypes.choices(), default=enums.ProviderTypes.PAYME.value)

    def validate_payment_method(self, value):
        if value not in enums.ProviderTypes.choices():
            raise_validation_error(_("Invalid payment method"))
        return value
