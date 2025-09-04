from uuid import UUID

from django.utils.translation import gettext_lazy as _
from django.db.models import F, Count, Sum


from apps.shared.utils.logging import logger
from apps.sport.models import Result, Tournament


class ScoringService:

    @staticmethod
    def update_points(sportsman, old_rating, new_rating, tournament):
        """
        Update points for both sportsman and their trainer when result is created or updated.
        """
        ScoringService.update_sportsman_points(sportsman, old_rating, new_rating, tournament)

        sportsman_profile = sportsman.sportsman_profile
        trainer_profile = sportsman_profile.trainer

        if trainer_profile:
            logger.info(f"Updating trainer points for {trainer_profile.user.username}")
            ScoringService.update_trainer_points(trainer_profile.user, tournament, new_rating)

    @staticmethod
    def update_sportsman_points(sportsman, old_rating, new_rating, tournament):
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
    def update_trainer_points(trainer, tournament, rating):
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
        Recalculates points for all sportsmen and their trainers in a tournament.
        Trainer points = average of their sportsmen's points.
        """
        tournament: Tournament = Tournament.objects.filter(id=tournament_id).first()
        logger.info(f"Recalculating points for tournament: {tournament.name} (ID: {tournament.id})")
        from apps.user.models import Sportsman, Trainer

        results = Result.objects.filter(tournament=tournament, is_verified=True)

        sportsman_scores: dict[int, int] = {}   # {sportsman_user_id: points}
        trainer_sportsmen: dict[int, list[int]] = {}  # {trainer_user_id: [sportsman_user_id, ...]}

        # --- 1. Calculate sportsman scores
        for result in results:
            sportsman_user_id = result.user_id
            trainer_user_id = result.trainer.user_id if result.trainer else None

            score = tournament.get_score(result.rating)
            sportsman_scores[sportsman_user_id] = sportsman_scores.get(sportsman_user_id, 0) + score

            if trainer_user_id:
                trainer_sportsmen.setdefault(trainer_user_id, []).append(sportsman_user_id)

        # --- 2. Bulk update Sportsman
        sportsmen = list(Sportsman.objects.filter(user_id__in=sportsman_scores.keys()))
        for s in sportsmen:
            s.points = sportsman_scores[s.user_id]
        Sportsman.objects.bulk_update(sportsmen, ["points"])

        # --- 3. Calculate trainer averages
        trainers = (
            Trainer.objects
            .filter(user_id__in=trainer_sportsmen.keys())
            .annotate(
                total_points=Sum('sportsmen__points'),
                count=Count('sportsmen__user_id')
            )
        )

        for t in trainers:
            total = t.total_points or 0
            count = t.count or 0
            logger.info(f"Trainer {t.user.username} - Total Points: {total}, Count: {count}")
            t.points = total / count if count > 0 else 0

        Trainer.objects.bulk_update(trainers, ['points'])

        logger.info(f"Recalculated {len(sportsmen)} sportsmen and {len(trainers)} trainers")
