import typing as t

from uuid import UUID

from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet, Model
from django.utils.functional import Promise
from google_crc32c import value

from apps.user.models import (
    User,
    Sportsman,
    Trainer,
    UserRequest,
)
from apps.federation.models import (
    Federation
)
from apps.shared.utils.types import *
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.logging import logger
import apps.shared.utils.enums as enums
from apps.sport.models import Result
from apps.shared.services.scoring_service import ScoringService
from apps.shared.utils.payloads import (
    SPORTSMAN_APPROVAL_REQUIRED_FIELDS,
    TRAINER_APPROVAL_REQUIRED_FIELDS,
    TRAINER_FEDERATION_ADMIN_APPROVAL_REQUIRED_FIELDS
)


class SnapshotService:

    # @staticmethod
    # def prepare_user_snapshot(
    #         instance: Sportsman,
    #         data: dict,
    #         request_type: str
    #     ) -> tuple[dict | None, dict | None]:
    #     """
    #     Determines if a snapshot is needed and returns old and new snapshots with request_type.
    #     """
    #     flattened_data = data.copy()
    #     logger.info(f"Flattened data for snapshot: {flattened_data}")

    #     old_snapshot, new_snapshot = SnapshotService.build_snapshot(
    #         model=instance, request_type=request_type, data=flattened_data
    #     )
    #     logger.debug(f"Old Snapshot: {old_snapshot}, New Snapshot: {new_snapshot}")
    #     return old_snapshot, new_snapshot

    @staticmethod
    def build_snapshot(
        model: ModelT,
        request_type: str,
        data: dict | None = None
    ) -> tuple[dict | None, dict | None]:
        """
        Builds a snapshot (dict) of important model fields
        Requirements:
        - model instance for `old_snapshot`
        - data for `new_snapshot`

        - `old_snapshot`: The state of the model before any changes
        - `new_snapshot`: The state of the model after changes

        """
        function_mapping: dict[str, t.Callable[[t.Any, dict], tuple[dict | None, dict | None]]] = {
            "federation_admin_request": SnapshotService._build_user_federation_snapshot,
            "sportsman_trainer_request": SnapshotService._build_sportsman_snapshot,
            "trainer_federation_request": SnapshotService._build_trainer_snapshot,
        }
        return function_mapping.get(request_type, lambda x, y: (None, None))(model, data)

    @staticmethod
    def _build_user_federation_snapshot(user: User, data: dict) -> tuple[dict | None, dict | None]:
        """
        Builds a snapshot of the user's federation information.
        """
        new_snapshot = {}

        for field in TRAINER_FEDERATION_ADMIN_APPROVAL_REQUIRED_FIELDS:
            value = getattr(user, field, None)
            new_snapshot[field] = SnapshotService._serialize_value(value)

        new_snapshot["id"] = str(user.id)

        return None, new_snapshot

    @staticmethod
    def _build_sportsman_snapshot(sportsman: Sportsman, data: dict) -> tuple[dict | None, dict | None]:
        """
        Returns (old_snapshot, new_snapshot) with all required fields included,
        even if missing in validated_data.
        """
        old_snapshot = {}
        new_snapshot = {}

        for field in SPORTSMAN_APPROVAL_REQUIRED_FIELDS:
            old_value = getattr(sportsman, field, None)
            new_value = data.get(field, old_value)

            old_snapshot[field] = SnapshotService._serialize_value(old_value)
            new_snapshot[field] = SnapshotService._serialize_value(new_value)

        return old_snapshot, new_snapshot

    @staticmethod
    def _build_trainer_snapshot(trainer: Trainer, data: dict) -> tuple[dict | None, dict | None]:
        """
        Returns (old_snapshot, new_snapshot) with all required fields included,
        even if missing in validated_data.
        """
        old_snapshot = {}
        new_snapshot = {}

        for field in TRAINER_APPROVAL_REQUIRED_FIELDS:
            old_value = getattr(trainer, field, None)
            new_value = data.get(field, old_value)

            old_snapshot[field] = SnapshotService._serialize_value(old_value)
            new_snapshot[field] = SnapshotService._serialize_value(new_value)

        return old_snapshot, new_snapshot

    @staticmethod
    def _serialize_value(value: t.Any) -> t.Union[dict, t.Any]:
        """Helper to make values JSON-serializable."""
        if hasattr(value, 'pk'):
            return {'id': str(value.pk), 'name': str(value)}
        return str(value)
