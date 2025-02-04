from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from user.models import Sportsman, Trainer, Result
from shared.addons.custom_logging import logger

@receiver(post_save, sender=Result)
def update_trainer_results(sender, instance, created, **kwargs):
    """
    Update the trainer's results whenever a new result is created for a sportsman.
    Ignore if the result is the trainer's own result.
    """
    if created and instance.trainer and instance.sportsman_profile:
        logger.info(f"Signal triggered")
        trainer_profile = instance.trainer
        
        tournament = instance.tournament
        rating = instance.rating

        # Check if the trainer already has a result for this tournament
        trainer_result = Result.objects.filter(trainer_profile=trainer_profile, tournament=tournament, currently_participating=False).first()
    
        # Determine the value to increment based on the rating
        increment_field = None
        if rating == 1:
            increment_field = 'number_of_gold'
        elif rating == 2:
            increment_field = 'number_of_silver'
        elif rating == 3:
            increment_field = 'number_of_bronze'

        if trainer_result:
            logger.info(f"(post_save) Results exists, updating it...")
            # Increment the appropriate field
            if increment_field:
                setattr(trainer_result, increment_field, getattr(trainer_result, increment_field) + 1)
            trainer_result.save()
        else:
            logger.info(f"(post_save) Result does not exist or trainer participated in tournament: {trainer_result.tournament.name if trainer_result else None}, creating...")
            # Create a new result
            Result.objects.create(
                trainer_profile=trainer_profile,
                tournament=tournament,
                country=instance.country,
                year=instance.year,
                currently_participating=False,
                rating=0,
                number_of_gold=(1 if rating == 1 else 0),
                number_of_silver=(1 if rating == 2 else 0),
                number_of_bronze=(1 if rating == 3 else 0)
            )


@receiver(pre_delete, sender=Result)
def update_or_delete_trainer_result(sender, instance, **kwargs):
    """
    This signal runs before deleting a sportsman's result.
    It checks whether the trainer has results from other sportsmen
    in the same tournament and updates or deletes them accordingly.
    """
    if instance.trainer:
        trainer_profile = instance.trainer
        tournament = instance.tournament
        rating = instance.rating

        # Determine the value to decrement based on the rating
        decrement_field = None
        if rating == 1:
            decrement_field = 'number_of_gold'
        elif rating == 2:
            decrement_field = 'number_of_silver'
        elif rating == 3:
            decrement_field = 'number_of_bronze'

        # Check if other sportsmen have results for the same trainer & tournament
        other_sportsman_results = Result.objects.filter(trainer=trainer_profile, tournament=tournament).exclude(id=instance.id)
        
        if other_sportsman_results.exists():
            logger.info(f"(pre_delete) Other sportsmans exists in trainer's result, updating it...")
            # If other sportsmen exist, subtract the counts instead of deleting
            trainer_result = Result.objects.filter(trainer_profile=trainer_profile, tournament=tournament, currently_participating=False).first()
            if trainer_result and decrement_field:
                setattr(trainer_result, decrement_field, getattr(trainer_result, decrement_field) -1)
            trainer_result.save()
        else:
            logger.info(f"(pre_delete) No other sportsmans exists in trainer's result, deleting it...")
            # If no other sportsman exist in trainer's result, delete the result entirely
            Result.objects.filter(trainer_profile=trainer_profile, tournament=tournament, currently_participating=False).delete()
