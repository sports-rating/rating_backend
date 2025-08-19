from django.utils.translation import gettext_lazy as _
from django.db.models import F

from apps.shared.utils.logging import logger


class ScoringService:
    @staticmethod
    def update_sportsman_points(sportsman, instance, tournament, rating):
        """
        Update sportsman's points when rating or tournament changes.
        Subtracts old score and adds new score.
        """
        # --- Step 1: old score ---
        old_score = instance.tournament.get_score(instance.rating)
        logger.info(f"Old score: {old_score}")  # LOGGING

        # --- Step 2: new score ---
        logger.info(f"Rating: {rating}")  # LOGGING
        new_score = tournament.get_score(rating)
        logger.info(f"New score: {new_score}")  # LOGGING

        sportsman.sportsman_profile.points = F("points") - old_score + new_score
        sportsman.sportsman_profile.save(update_fields=["points"])

        sportsman.sportsman_profile.refresh_from_db(fields=["points"])

        logger.info(f"Updated points for {sportsman}: {sportsman.sportsman_profile.points}")  # LOGGING
        return sportsman.sportsman_profile
