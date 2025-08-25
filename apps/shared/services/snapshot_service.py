import typing as t

from uuid import UUID

from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet, Model
from django.utils.functional import Promise

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


class SnapshotService:

    @staticmethod
    def prepare_user_snapshot(
            instance: Sportsman,
            data: dict,
            request_type: str
        ) -> tuple[dict | None, dict | None]:
        """
        Determines if a snapshot is needed and returns old and new snapshots with request_type.
        """
        flattened_data = data.copy()
        logger.info(f"Flattened data for snapshot: {flattened_data}")

        # Merge flattened and profile data for snapshot
        merged_data = {**flattened_data}
        logger.debug(f"Merged Data for Snapshot: {merged_data}")
        old_snapshot, new_snapshot = SnapshotService.build_snapshot(
            model=instance, request_type=request_type, data=merged_data
        )
        logger.debug(f"Old Snapshot: {old_snapshot}, New Snapshot: {new_snapshot}")
        return old_snapshot, new_snapshot

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
        }
        return function_mapping.get(request_type, lambda x, y: (None, None))(model, data)

    @staticmethod
    def _build_user_federation_snapshot(user: User, data: dict) -> tuple[dict | None, dict | None]:
        """
        Builds a snapshot of the user's federation information.
        """
        return None, {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "birth_date": user.birth_date.isoformat() if user.birth_date else None,
            "email": user.email,
            "user_role": user.user_role,
        }

    @staticmethod
    def _build_sportsman_snapshot(sportsman: Sportsman, data: dict) -> tuple[dict | None, dict | None]:
        """
        Builds a snapshot of the user's sportsman information.
        """

        old_snapshot: dict = {
            "height": str(sportsman.height),
            "weight": str(sportsman.weight),
            "sport_rank": sportsman.sport_rank,
        }


        new_snapshot: dict = {
            "height": str(data.get("height", sportsman.height)),
            "weight": str(data.get("weight", sportsman.weight)),
            "sport_rank": data.get("sport_rank", sportsman.sport_rank),
        }

        return old_snapshot, new_snapshot
