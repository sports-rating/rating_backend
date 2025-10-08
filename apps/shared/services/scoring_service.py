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
        old_score = tournament.get_score(old_rating) if old_rating else 0
        logger.info(f"Old score: {old_score}")  # LOGGING

        # --- Step 2: new score ---
        logger.info(f"Rating: {new_rating}")  # LOGGING
        new_score = tournament.get_score(new_rating) if new_rating else 0
        logger.info(f"New score: {new_score}")  # LOGGING

        delta = new_score - old_score
        if delta != 0:
            sportsman.sportsman_profile.points = F("points") + delta
            sportsman.sportsman_profile.save(update_fields=["points"])
            sportsman.sportsman_profile.refresh_from_db(fields=["points"])
            logger.info(
                f"Updated points for {sportsman.username}: {delta:+} → {sportsman.sportsman_profile.points}"
            )
        # sportsman.sportsman_profile.points = F("points") - old_score + new_score
        # sportsman.sportsman_profile.save(update_fields=["points"])

        # sportsman.sportsman_profile.refresh_from_db(fields=["points"])

        # logger.info(f"Updated points for {sportsman}: {sportsman.sportsman_profile.points}")  # LOGGING

    @staticmethod
    def update_trainer_points(
            trainer: User | None,
            tournament: Tournament,
            rating: int | None
        ):
        """
        Update trainer's points whenever a result involving them is created or modified.
        New logic:
        - Sum all verified results' scores where this trainer is assigned
        - Divide by distinct count of sportsmen (user) in those results
        """
        if not trainer or not hasattr(trainer, "trainer_profile"):
            logger.warning("Trainer not found or has no trainer profile.")
            return

        results_qs = trainer.trainer_profile.assisted_results.filter(is_verified=True)

        if not results_qs.exists():
            trainer.trainer_profile.points = 0
        else:
            # --- Sum of all scores ---
            total_points = sum(result.tournament.get_score(result.rating) for result in results_qs)

            # --- Count of distinct sportsmen trained in those results ---
            distinct_sportsmen_count = results_qs.values("user").distinct().count()

            # --- Compute average ---
            trainer_points = (
                round(total_points / distinct_sportsmen_count, 2)
                if distinct_sportsmen_count > 0 else 0
            )

            if trainer.trainer_profile.points != trainer_points:
                logger.info(
                    f"Updated points for trainer {trainer.username}: "
                    f"{trainer.trainer_profile.points} → {trainer_points}"
                )
                trainer.trainer_profile.points = trainer_points

        logger.info(f"Updated points for trainer {trainer}: {trainer.trainer_profile.points}")  # LOGGING
        trainer.trainer_profile.save(update_fields=["points"])

    @staticmethod
    def recalculate_points_for_tournament(tournament_id: UUID) -> None:
        """
        Recalculate points for sportsmen who have results in the given tournament.
        For each impacted sportsman, recompute their TOTAL points across ALL tournaments.
        Then recompute points for their trainers (average of sportsmen points).
        """
        from apps.user.models import Sportsman, Trainer
        from apps.sport.models import Tournament  # adjust import paths
        from apps.career.models import Result

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
                        .prefetch_related("assisted_results__tournament")
                )
                trainers_to_update = []
                for trainer in trainers:
                    results = trainer.assisted_results.filter(is_verified=True)
                    total_points = 0
                    if not results.exists():
                        trainer.points = 0
                        trainers_to_update.append(trainer)
                    else:
                        # Sum all result scores
                        for result in results:
                            if result.tournament and result.rating:
                                score = result.score
                                logger.info(f"Result {result.id} | Rating: {result.rating} | score: {score}")  # LOGGING
                                total_points += float(score)
                            else:
                                logger.warning(f"Skipping result {result.id}: no rating")
                                continue

                        # Count distinct sportsmen this trainer worked with
                        distinct_sportsmen_count = results.values("user").distinct().count()

                        # Avoid division by zero (if no valid sportsmen)
                        if distinct_sportsmen_count == 0:
                            trainer.points = 0
                        else:
                            trainer.points = round((total_points / distinct_sportsmen_count), 2)

                        trainers_to_update.append(trainer)

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
            trainers = Trainer.objects.prefetch_related("assisted_results__tournament")

            for trainer in trainers:
                results = trainer.assisted_results.filter(is_verified=True)
                total_points = 0
                trainer_points = 0
                if not results.exists():
                    trainer.points = 0
                else:
                    # Sum all result scores
                    for result in results:
                        if result.tournament and result.rating:
                            score = result.score
                            logger.info(f"Result {result.id} | Rating: {result.rating} | score: {score}")  # LOGGING
                            total_points += float(score)

                    # Count distinct sportsmen this trainer worked with
                    distinct_sportsmen_count = results.values("user").distinct().count()

                    # Avoid division by zero (if no valid sportsmen)
                    if distinct_sportsmen_count == 0:
                        trainer_points = 0
                    else:
                        trainer_points = round((total_points / distinct_sportsmen_count), 2)

                    if trainer.points != trainer_points:
                        logger.info(f"Updating points for trainer {trainer.user.username} from {trainer.points} to {trainer_points}")
                        trainer.points = trainer_points

                trainer.save(update_fields=["points"])

            logger.info(f"Recalculated points for {trainers.count()} trainers.")
