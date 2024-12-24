from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import generics, permissions, status, filters as rest_framework_filters

from shared.addons.pagination import CustomPagination
from shared.addons.utils import (
    success_response,
    error_response
)

from user.models import (
    User,
    Sportsman,
    Trainer,
)

from user.serializers import (
    UsersMeSerializer
)
from dashboard.serializers import (
    UserListSerializer
)

from .filters import (
    UserFilter,
)

from shared.addons.exceptions import raise_validation_error

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = (
        permissions.AllowAny,
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data, 
            message=_("Users list"),
            code=200,
        )




