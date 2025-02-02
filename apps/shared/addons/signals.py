from django.db.models.signals import post_save
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
        trainer_profile = instance.trainer
        
        tournament = instance.tournament
        rating = instance.rating

        # Check if the trainer already has a result for this tournament
        existing_result = Result.objects.filter(trainer_profile=trainer_profile, tournament=tournament).first()

        # Determine the value to increment based on the rating
        increment_field = None
        if rating == 1:
            increment_field = 'number_of_gold'
        elif rating == 2:
            increment_field = 'number_of_silver'
        elif rating == 3:
            increment_field = 'number_of_bronze'

        if existing_result:
            # Increment the appropriate field
            if increment_field:
                setattr(existing_result, increment_field, getattr(existing_result, increment_field) + 1)
            existing_result.save()
        else:
            # Create a new result
            Result.objects.create(
                trainer_profile=trainer_profile,
                tournament=tournament,
                country=instance.country,
                year=instance.year,
                number_of_gold=(1 if rating == 1 else 0),
                number_of_silver=(1 if rating == 2 else 0),
                number_of_bronze=(1 if rating == 3 else 0)
            )

