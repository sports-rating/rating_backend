from django.contrib.auth import get_user_model

from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated

from apps.shared.utils.enums import UserRoles

User = get_user_model()


class IsOrdinaryUser(IsAuthenticated):
    message = "You must be ordinary user"

    def has_permission(self, request: Request, view) -> bool:
        return bool(
            super().has_permission(request, view)
            and request.user.user_role == UserRoles.ORDINARY.value
        )


class IsAdmin(IsAuthenticated):
    message = "You must be admin"

    def has_permission(self, request: Request, view) -> bool:
        return bool(
            super().has_permission(request, view)
            and (
                request.user.user_role == UserRoles.ADMIN.value
                or request.user.is_superuser
            )
        )
