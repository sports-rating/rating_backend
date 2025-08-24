from rest_framework.request import Request


class RequestContextMixin:
    """
    Implements request property for serializers (from context).

    If serializer does not contain request in context,
    it will raise RunTimeError not while the server is running
    and whole process is running.

    Prevention of future bugs!
    """

    @property
    def request(self) -> Request:
        if (request := self.context.get("request")) is None:
            raise RuntimeError("request was not provided in serializer context.")

        return request
