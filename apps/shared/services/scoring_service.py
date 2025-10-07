from uuid import UUID

from django.utils.translation import gettext_lazy as _
from django.db.models import F, Count, Sum, Prefetch
from django.db import transaction, models
from collections import defaultdict

from apps.shared.utils.logging import logger
from apps.shared.entities import (
    User,
    Tournament,
)


class ScoringService:

    @staticmethod
    def update_points(
        sportsman: User,
        trainer: User | None,
        old_rating: int | None,
        new_rating: int | None,
        tournament: Tournament
    ) -> None:
        """
        Update points for both sportsman and their trainer when result is created or updated.
        """
        ScoringService.update_sportsman_points(sportsman, old_rating, new_rating, tournament)

        sportsman_profile = sportsman.sportsman_profile
        # trainer_profile = sportsman_profile.trainer
        trainer_profile = trainer.trainer_profile if trainer else None

        if trainer_profile:
            logger.info(f"Updating trainer points for {trainer_profile.user.username}")
            ScoringService.update_trainer_points(trainer_profile.user, tournament, new_rating)

    @staticmethod
    def update_sportsman_points(
        sportsman: User,
        old_rating: int | None,
        new_rating: int | None,
        tournament: Tournament
    ) -> None:
        """
        Update sportsman's points when result is firstly created.
        Subtracts old score and adds new score.
        """
        # --- Step 1: old score ---
        old_score = tournament.get_score(old_rating)
        logger.info(f"Old score: {old_score}")  # LOGGING

        # --- Step 2: new score ---
        logger.info(f"Rating: {new_rating}")  # LOGGING
        new_score = tournament.get_score(new_rating)
        logger.info(f"New score: {new_score}")  # LOGGING

        sportsman.sportsman_profile.points = F("points") - old_score + new_score
        sportsman.sportsman_profile.save(update_fields=["points"])

        sportsman.sportsman_profile.refresh_from_db(fields=["points"])

        logger.info(f"Updated points for {sportsman}: {sportsman.sportsman_profile.points}")  # LOGGING
        return sportsman.sportsman_profile

    @staticmethod
    def update_trainer_points(
            trainer: User | None,
            tournament: Tournament,
            rating: int | None
        ):
        """
        Update trainer's points when result is firstly created.
        """
        qs = trainer.trainer_profile.sportsmen.all()
        result = qs.aggregate(total_points=Sum('points'), count=Count('user_id'))

        total_points = result['total_points'] or 0
        count = result['count'] or 0

        trainer.trainer_profile.points = (
            total_points / count if count > 0 else 0
        )
        logger.info(f"Updated points for trainer {trainer}: {trainer.trainer_profile.points}")  # LOGGING
        trainer.trainer_profile.save(update_fields=['points'])

    @staticmethod
    def recalculate_points_for_tournament(tournament_id: UUID) -> None:
        """
        Recalculate points for sportsmen who have results in the given tournament.
        For each impacted sportsman, recompute their TOTAL points across ALL tournaments.
        Then recompute points for their trainers (average of sportsmen points).
        """
        from apps.user.models import Sportsman, Trainer
        from apps.sport.models import Result, Tournament  # adjust import paths

        with transaction.atomic():
            # 1) Who is impacted by this tournament's policy change?
            impacted_user_ids = list(
                Result.objects
                    .filter(tournament_id=tournament_id, is_verified=True)
                    .values_list("user_id", flat=True)
                    .distinct()
            )
            if not impacted_user_ids:
                return

            # 2) Pull ALL verified results for these sportsmen (across ALL tournaments)
            results = (
                Result.objects
                    .filter(user_id__in=impacted_user_ids, is_verified=True)
                    .select_related("tournament")  # so get_score can use policy without extra queries
            )

            # 3) Sum points per sportsman using each result's tournament policy
            points_by_user = defaultdict(float)
            for r in results:
                # tournament.get_score(r.rating) should return the configured score for that rating
                score = r.tournament.get_score(r.rating)
                # If your get_score returns Decimal, cast to float if you keep Sportsman.points as FloatField
                points_by_user[r.user_id] += float(score)

            # 4) Bulk update Sportsman.points for impacted users
            sportsmen = list(Sportsman.objects.filter(user_id__in=points_by_user.keys()))
            for s in sportsmen:
                s.points = points_by_user.get(s.user_id, 0.0)
            Sportsman.objects.bulk_update(sportsmen, ["points"])

            # 5) Recompute trainer averages ONLY for trainers of impacted sportsmen
            trainer_ids = list(
                Sportsman.objects
                        .filter(user_id__in=points_by_user.keys(), trainer__isnull=False)
                        .values_list("trainer_id", flat=True)
                        .distinct()
            )

            if trainer_ids:
                trainers = (
                    Trainer.objects
                        .filter(user_id__in=trainer_ids)
                        .annotate(
                            total_points=Sum("sportsmen__points"),
                            count=Count("sportsmen__user_id"),
                        )
                )
                trainers_to_update = []
                for t in trainers:
                    t.points = (t.total_points or 0) / (t.count or 1) if t.count else 0
                    trainers_to_update.append(t)
                if trainers_to_update:
                    Trainer.objects.bulk_update(trainers_to_update, ["points"])

    @staticmethod
    def recalculate_all_points() -> None:
        """
        Recalculate points for all sportsmen and their trainers.
        """
        from apps.user.models import Sportsman, Trainer
        from apps.sport.models import Tournament
        from apps.career.models import Result

        with transaction.atomic():
            # --- Step 1: Recalculate Sportsman Points ---
            sportsmen = (
                Sportsman.objects
                .select_related("user")
                .prefetch_related(
                    Prefetch(
                        "user__results",
                        queryset=Result.objects.filter(is_verified=True)
                        .select_related("tournament"),
                        to_attr="verified_results"
                    )
                )
            )

            for sportsman in sportsmen:
                total_points = 0
                for result in getattr(sportsman.user, "verified_results", []):
                    if result.tournament and result.rating:
                        score = result.tournament.get_score(result.rating)
                        total_points += float(score)

                if sportsman.points != total_points:
                    logger.info(f"Updating points for sportsman {sportsman.user.username} from {sportsman.points} to {total_points}")
                    sportsman.points = total_points
                    sportsman.save(update_fields=["points"])

            logger.info(f"Recalculated points for {sportsmen.count()} sportsmen.")

            # --- Step 2: Recalculate Trainer Points ---
            trainers = Trainer.objects.prefetch_related("sportsmen")

            for trainer in trainers:
                sportsmen = trainer.sportsmen.all()
                if not sportsmen.exists():
                    trainer.points = 0
                else:
                    total_sportsman_points = sum(s.points for s in sportsmen)
                    trainer_points = total_sportsman_points / sportsmen.count()
                    if trainer.points != trainer_points:
                        logger.info(f"Updating points for trainer {trainer.user.username} from {trainer.points} to {trainer_points}")
                        trainer.points = trainer_points

                trainer.save(update_fields=["points"])

            logger.info(f"Recalculated points for {trainers.count()} trainers.")
