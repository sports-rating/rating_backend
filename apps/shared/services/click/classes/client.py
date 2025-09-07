import typing as t
import base64
import time
import hashlib
import requests
import json

from uuid import UUID

from django.conf import settings
from apps.shared.utils.logging import logger


class Click:
    """
    The Click class provides a simple interface
    """
    def __init__(
        self,
        service_id: int,
        merchant_id: int,
        merchant_user_id: int = None,
        secret_key: str = None,
    ) -> None:
        self.service_id = service_id
        self.merchant_id = merchant_id
        self.merchant_user_id = merchant_user_id or settings.CLICK_MERCHANT_USER_ID
        self.secret_key = secret_key or settings.CLICK_SECRET_KEY
        self.invoice_url = "https://api.click.uz/v2/merchant"
        self.payment_url = "https://my.click.uz/services/pay"

    class ACTION:
        PREPARE = '0'
        COMPLETE = '1'

        ALLOWED_ACTIONS = [
            PREPARE,
            COMPLETE
        ]

    def _post(self, url: str, headers: dict, body: dict, timeout=10) -> dict:
        """
        Internal method to send a POST request.

        args:
            url (str): The URL to send the POST request to.
            headers (dict): The headers to include in the request.
            body (dict): The body of the request.
            timeout (int, optional): Timeout for the request in seconds. Defaults to 10.

        returns:
            dict: The JSON response from the request.
        """

        data = json.dumps(body)
        result = requests.request(
            method="POST",
            url=url,
            headers=headers,
            data=data,
            timeout=timeout
        )
        result.raise_for_status()
        return result.json()

    def generate_payment_link(self, id: UUID, amount: float) -> str:
        """
        Generate a payment link for CLICK.

        :param id: The internal transaction id.
        :param amount: The amount to be paid.
        """
        payment_link = (
            f"{self.payment_url}?service_id={self.service_id}&merchant_id={self.merchant_id}"
            f"&amount={amount}&transaction_param={id}"
            f"&return_url={settings.PAYME_RETURN_URL}"
        )
        logger.info(f"Click Payment Link: {payment_link}")
        return payment_link

    def create_invoice(
            self,
            amount: float,
            phone_number: str,
            merchant_trans_id: t.Optional[str] = None
        ):
        """
        Create an invoice using the CLICK API.

        args:
            amount (float): Requested amount.
            phone_number (str): The phone number associated with the invoice.
        returns:
            dict: The response from the CLICK API.
        """
        timestamp = int(time.time())
        digest_input = f"{timestamp}{self.secret_key}"
        digest = hashlib.sha1(digest_input.encode()).hexdigest()
        headers = {
            "Auth": f"{self.merchant_user_id}:{digest}:{timestamp}",
        }
        body = {
            "service_id": self.service_id,
            "amount": amount,
            "phone_number": phone_number,
            "merchant_trans_id": self.merchant_user_id
        }
        logger.info(f"Click Invoice Body: {body}")  # LOGGING

        url = f"{self.invoice_url}/invoice/create"
        return self._post(url, headers, body, 10)


click = Click(
    service_id=settings.CLICK_SERVICE_ID,
    merchant_id=settings.CLICK_MERCHANT_ID,
    secret_key=settings.CLICK_SECRET_KEY,
    merchant_user_id=settings.CLICK_MERCHANT_USER_ID,
)

Action = Click.ACTION

__all__ = ("click", "Action")
