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


class CheckoutSerializer(RequestContextMixin, serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=enums.ProviderTypes.choices(), default=enums.ProviderTypes.PAYME.value)
    section_type = serializers.ChoiceField(choices=enums.SectionTypes.choices(), required=True)

    def validate_payment_method(self, value):
        logger.debug(f"Validating payment method: {value}")
        logger.info(f"Available payment methods: {enums.ProviderTypes.values()}")
        if value not in enums.ProviderTypes.values():
            raise_validation_error(message=_("Invalid payment method selected!"))
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.sportsman_profile:
            raise_validation_error(message=_("User does not have a sportsman profile!"))

        if not user.sportsman_profile.is_sportsman_verified:
            raise_validation_error(message=_("Sportsman is not verified!"))
        return attrs
