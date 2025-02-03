from django.db.models.signals import post_save
from django.dispatch import receiver
from user.models import Sportsman, Trainer
from sport.models import Result
from shared.addons.custom_logging import logger

@receiver(post_save, sender=Result)
def update_trainer_results(sender, instance, created, **kwargs):
    """
    Update the trainer's results whenever a new result is created for a sportsman.
    Ignore if the result is the trainer's own result.
    """
    if created and instance.trainer:
        if instance.user and instance.user.user_role=='sportsman':
            trainer_profile = instance.trainer
            
            tournament = instance.tournament
            rating = instance.rating

            # Check if the trainer already has a result for this tournament
            existing_result = Result.objects.filter(user=trainer_profile.user, tournament=tournament).first()

            # Determine the value to increment based on the rating
            increment_field = None
            if rating == 1:
                increment_field = 'gold'
            elif rating == 2:
                increment_field = 'silver'
            elif rating == 3:
                increment_field = 'bronze'

            if existing_result:
                # Increment the appropriate field
                if increment_field:
                    setattr(existing_result, increment_field, getattr(existing_result, increment_field) + 1)
                existing_result.save()
            else:
                # Create a new result
                Result.objects.create(
                    user=trainer_profile.user,
                    tournament=tournament,
                    country=instance.country,
                    year=instance.year,
                    gold=(1 if rating == 1 else 0),
                    silver=(1 if rating == 2 else 0),
                    bronze=(1 if rating == 3 else 0)
                )
