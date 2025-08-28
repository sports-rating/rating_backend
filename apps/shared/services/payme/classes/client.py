import typing as t
import base64
from uuid import UUID

from django.conf import settings
from apps.shared.utils.logging import logger


class Payme:
    """
    The Payme class provides a simple interface
    """
    def __init__(
        self,
        payme_id: str,
        fallback_id: t.Optional[str] = None,
        payme_key: t.Optional[str] = None,
        is_test_mode: bool = True
    ) -> None:
        self.payme_id = payme_id
        self.fallback_id = fallback_id
        self.payme_key = settings.PAYME_KEY if not is_test_mode else settings.PAYME_TEST_KEY
        self.is_test_mode = is_test_mode

        # self.url = settings.PAYME_PROD_URL if not is_test_mode else settings.PAYME_TEST_URL

    def generate_payment_link(self, id: UUID, amount: float) -> str:
        """
        Generate a payment link for a specific order.

        This method encodes the payment parameters into a base64 string and
        constructs a URL for the Payme checkout.
        """
        amount = amount * 100 # Convert amount to the smallest currency unit (tiyin)
        params = f"m={self.payme_id};ac.{settings.PAYME_ACCOUNT_FIELD}={id};a={amount};c={settings.PAYME_RETURN_URL}"
        logger.info(f"Payme Params: {params}")  # LOGGING

        params = base64.b64encode(params.encode("utf-8")).decode("utf-8")


        if self.is_test_mode:
            return f"https://test.paycom.uz/{params}"

        return f"https://checkout.paycom.uz/{params}"


payme = Payme(
    payme_id=settings.PAYME_ID,
    is_test_mode=settings.PAYME_IS_TEST_MODE,
)

__all__ = ("payme",)
