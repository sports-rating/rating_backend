import typing as t
from dataclasses import dataclass, field


class WebhookResponse:
    """
    The webhook response structure for payme
    """

    def as_resp(self):
        response = {"result": {}}
        for key, value in self.__dict__.items():
            response["result"][key] = value
        return response


@dataclass
class CreateTransaction(WebhookResponse):
    """
    The Create transaction request
    """
    transaction: str
    state: int
    create_time: int


@dataclass
class PerformTransaction(WebhookResponse):
    """
    The perform transaction response
    """
    transaction: str
    state: str
    perform_time: int


@dataclass
class CancelTransaction(WebhookResponse):
    """
    The cancel transaction request
    """
    transaction: str
    state: str
    cancel_time: str


@dataclass
class CheckTransaction(WebhookResponse):
    """
    The check transaction request
    """

    transaction: str
    state: str
    reason: str
    create_time: int
    perform_time: t.Optional[int] = None
    cancel_time: t.Optional[int] = None



@dataclass
class GetStatement(WebhookResponse):
    """
    The check perform transactions response
    """

    transactions: t.List[t.Dict[str, str | int | t.Dict[str, str | int]]]


@dataclass
class SetFiscalData(WebhookResponse):
    """
    The set fiscal data request
    """

    success: bool
