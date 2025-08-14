from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.shared.utils.logging import logger

from apps.user.models import Sportsman, Trainer
from apps.sport.models import Result


@receiver(post_save, sender=Result)
def update_trainer_results(sender, instance, created, **kwargs):
    """
    Update the trainer's results whenever a new result is created for a sportsman.
    Ignore if the result is the trainer's own result.
    """
    if created and instance.trainer and instance.user:
        logger.info(f"Signal triggered")
        trainer_profile = instance.trainer

        tournament = instance.tournament
        rating = instance.rating

        # Check if the trainer already has a result for this tournament
        trainer_result = Result.objects.filter(user=trainer_profile.user, tournament=tournament, currently_participating=False).first()

        # Determine the value to increment based on the rating
        increment_field = None
        if rating == 1:
            increment_field = 'gold'
        elif rating == 2:
            increment_field = 'silver'
        elif rating == 3:
            increment_field = 'bronze'

        if trainer_result:
            logger.info(f"(post_save) Results exists, updating it...")
            # Increment the appropriate field
            if increment_field:
                setattr(trainer_result, increment_field, getattr(trainer_result, increment_field) + 1)
            trainer_result.save()
        else:
            logger.info(f"(post_save) Result does not exist or trainer participated in tournament: {trainer_result.tournament.name if trainer_result else None}, creating...")
            # Create a new result
            result = Result.objects.create(
                user=trainer_profile.user,
                tournament=tournament,
                country=instance.country,
                year=instance.year,
                currently_participating=False,
                rating=0,
                gold=(1 if rating == 1 else 0),
                silver=(1 if rating == 2 else 0),
                bronze=(1 if rating == 3 else 0)
            )
            logger.info(f"(post_save) Currently_participating: {result.currently_participating}")


@receiver(pre_delete, sender=Result)
def update_or_delete_trainer_result(sender, instance, **kwargs):
    """
    This signal runs before deleting a sportsman's result.
    It checks whether the trainer has results from other sportsmen in the
    same tournament and updates or deletes them accordingly.
    """
    if instance.trainer:
        trainer_profile = instance.trainer
        tournament = instance.tournament
        rating = instance.rating

        # Determine the value to decrement based on the rating
        decrement_field = None
        if rating == 1:
            decrement_field = 'gold'
        elif rating == 2:
            decrement_field = 'silver'
        elif rating == 3:
            decrement_field = 'bronze'

        logger.info(f"Rating: {rating}")
        logger.info(f"Decrement field: {decrement_field}")
        logger.info(f"Tournament: {instance.tournament}")

        # Check if other sportsmen have results for the same trainer & tournament
        other_sportsman_results = Result.objects.filter(trainer=trainer_profile, tournament=tournament).exclude(id=instance.id)

        if other_sportsman_results.exists():
            logger.info(f"(pre_delete) Other sportsmans exists in trainer's result, updating it...")
            # If other sportsmen exist, subtract the counts instead of deleting
            trainer_result = Result.objects.filter(user=trainer_profile.user, tournament=tournament, currently_participating=False).first()
            if trainer_result and decrement_field:
                setattr(trainer_result, decrement_field, max(0, getattr(trainer_result, decrement_field) - 1))
            trainer_result.save()
        else:
            logger.info(f"(pre_delete) No other sportsmans exists in trainer's result, deleting it...")
            # If no other sportsman exist in trainer's result, delete the result entirely
            Result.objects.filter(user=trainer_profile.user, tournament=tournament, currently_participating=False).delete()
