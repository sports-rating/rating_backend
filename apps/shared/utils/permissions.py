from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated

from apps.shared.utils.enums import UserRoles

User = get_user_model()


class IsSuperAdmin(IsAuthenticated):
    message = _("You don't have super admin permissions!")

    def has_permission(self, request, view):
        return bool(
            super().has_permission(request, view)
            and request.user.user_role == UserRoles.SUPER_ADMIN.value
        )


class IsAdmin(IsAuthenticated):
    message = _("You don't have admin permissions!")

    def has_permission(self, request, view):
        return bool(
            super().has_permission(request, view)
            and request.user.user_role == UserRoles.ADMIN.value
        )


class IsAdminOrSuperAdmin(IsAuthenticated):
    message = _("You don't have admin or super admin permissions!")

    def has_permission(self, request, view):
        return bool(
            super().has_permission(request, view)
            and request.user.user_role in (
                UserRoles.ADMIN.value,
                UserRoles.SUPER_ADMIN.value,
            )
        )


class IsOrdinaryUser(IsAuthenticated):
    message = "You must be ordinary user"

    def has_permission(self, request: Request, view) -> bool:
        return bool(
            super().has_permission(request, view)
            and request.user.user_role in (
                UserRoles.ORDINARY.value,
                UserRoles.SPORTSMAN.value,
                UserRoles.TRAINER.value,
            )
        )
