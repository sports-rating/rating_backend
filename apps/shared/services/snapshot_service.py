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
    TRAINER_FEDERATION_ADMIN_APPROVAL_REQUIRED_FIELDS,
    SPORTSMAN_RESULT_APPROVAL_REQUIRED_FIELDS
)
from apps.shared.serializers import (
    SportsmanResultSnapshotSerializer,
    SportsmanSnapshotSerializer,
    TrainerSnapshotSerializer
)


class SnapshotService:

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
            "sportsman_result_verification_request": SnapshotService._build_sportsman_result_snapshot,
        }
        return function_mapping.get(request_type, lambda x, y: (None, None))(model, data)

    @staticmethod
    def apply_snapshot(instance: t.Union[Sportsman, Trainer, Result], snapshot: dict) -> None:
        serializer_class_map = {
            Sportsman: SportsmanSnapshotSerializer,
            Trainer: TrainerSnapshotSerializer,
            Result: SportsmanResultSnapshotSerializer,
        }
        serializer_class = serializer_class_map.get(type(instance))
        serializer = serializer_class(data=snapshot, partial=True)
        serializer.is_valid(raise_exception=True)

        for field, value in serializer.validated_data.items():
            if isinstance(value, dict) and 'id' in value:
                setattr(instance, f"{field}_id", value['id'])
            else:
                setattr(instance, field, None if value in (None, "None") else value)

        # Only save if not a Result instance
        if not isinstance(instance, Result):
            instance.save()

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
        serializer = SportsmanSnapshotSerializer()
        fields = serializer.get_fields().keys()

        def build_snapshot(source: dict | Sportsman) -> dict:
            return {
                field: SnapshotService._serialize_value(
                    source.get(field) if isinstance(source, dict) else getattr(source, field, None)
                )
                for field in fields
            }

        # Build old and new snapshots
        old_snapshot = build_snapshot(sportsman)
        new_snapshot = build_snapshot({**{f: getattr(sportsman, f, None) for f in fields}, **data})

        # Validate and normalize using serializer
        def validate(snapshot: dict) -> dict:
            s = SportsmanSnapshotSerializer(data=snapshot)
            s.is_valid(raise_exception=True)
            return s.data

        return validate(old_snapshot), validate(new_snapshot)

    @staticmethod
    def _build_trainer_snapshot(trainer: Trainer, data: dict) -> tuple[dict | None, dict | None]:
        """
        Returns (old_snapshot, new_snapshot) with all required fields included,
        even if missing in validated_data.
        """
        serializer = TrainerSnapshotSerializer()
        fields = serializer.get_fields().keys()

        def build_snapshot(source: dict | Trainer) -> dict:
            return {
                field: SnapshotService._serialize_value(
                    source.get(field) if isinstance(source, dict) else getattr(source, field, None)
                )
                for field in fields
            }

        # Build old and new snapshots
        old_snapshot = build_snapshot(trainer)
        new_snapshot = build_snapshot({**{f: getattr(trainer, f, None) for f in fields}, **data})

        def validate(snapshot: dict) -> dict:
            s = TrainerSnapshotSerializer(data=snapshot)
            s.is_valid(raise_exception=True)
            return s.data

        return validate(old_snapshot), validate(new_snapshot)

    # @staticmethod
    # def _build_sportsman_result_snapshot(result: Result, data: dict) -> tuple[dict | None, dict | None]:
    #     """
    #     Returns (new_snapshot) with all required fields included,
    #     even if missing in validated_data.
    #     """
    #     new_snapshot = {}

    #     for field in SPORTSMAN_RESULT_APPROVAL_REQUIRED_FIELDS:
    #         old_value = getattr(result, field, None)
    #         new_value = data.get(field, old_value)

    #         new_snapshot[field] = SnapshotService._serialize_value(new_value)

    #     return {}, new_snapshot

    @staticmethod
    def _build_sportsman_result_snapshot(result: Result, data: dict) -> dict:
        """
        Returns a validated snapshot dict using DRF serializer.
        """
        # Get all fields defined in serializer
        serializer_fields = SportsmanResultSnapshotSerializer().get_fields().keys()

        # Build a dict with either data-provided or fallback to model
        snapshot_data = {
            field: SnapshotService._serialize_value(data.get(field, getattr(result, field, None)))
            for field in serializer_fields
        }

        # Validate and normalize using the serializer
        serializer = SportsmanResultSnapshotSerializer(data=snapshot_data)
        serializer.is_valid(raise_exception=True)

        return {}, serializer.data


    @staticmethod
    def _serialize_value(value: t.Any) -> t.Union[dict, t.Any]:
        """Helper to make values JSON-serializable."""
        if hasattr(value, 'pk'):
            return {'id': str(value.pk), 'name': str(value.get_name)}
        return str(value)
