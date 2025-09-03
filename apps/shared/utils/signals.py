from django.db.models.signals import post_save, pre_delete, pre_save
from django.db.models import Avg, Sum, Count, Q
from django.dispatch import receiver

from apps.shared.utils.logging import logger

from apps.user.models import Sportsman, Trainer
from apps.sport.models import Result, Tournament
from apps.shared.utils import enums


def recalculate_points_for_tournament(tournament: Tournament):
    logger.info(f"Recalculating points for tournament: {tournament.name} (ID: {tournament.id})")
    from user.models import Sportsman, Trainer

    results = Result.objects.filter(tournament=tournament, is_verified=True)

    # Reset all scores
    sportsman_scores = {}
    trainer_scores = {}

    for result in results:
        sportsman_id = result.user.id
        trainer_id = result.trainer.user.id if result.trainer else None

        rating = result.rating
        score = tournament.get_score(rating)

        sportsman_scores[sportsman_id] = sportsman_scores.get(sportsman_id, 0) + score
        trainer_scores[trainer_id] = trainer_scores.get(trainer_id, 0) + score

    # Bulk update Sportsman
    Sportsman.objects.filter(id__in=sportsman_scores.keys()).update(points=0)
    for s_id, s_score in sportsman_scores.items():
        Sportsman.objects.filter(user_id=s_id).update(points=s_score)

    # Bulk update Trainer
    Trainer.objects.filter(id__in=trainer_scores.keys()).update(points=0)
    for t_id, t_score in trainer_scores.items():
        Trainer.objects.filter(user_id=t_id).update(points=t_score)


# -----------------------
# CREATE → post_save
# -----------------------
@receiver(post_save, sender=Result)
def handle_result_creation(sender, instance, created, **kwargs):
    if not created:
        return

    if not instance.trainer or not instance.user:
        return

    if not instance.is_verified:
        logger.info(f"Skipping creation for {instance} because result is not verified yet")
        return
    logger.info(f"Signal triggered for {instance} with created={created}")
    trainer_profile = instance.trainer
    tournament = instance.tournament

    # New result → add rating
    _increment_trainer_result(trainer_profile.user, tournament, instance.rating, instance)


# -----------------------
# UPDATE → pre_save
# -----------------------
@receiver(pre_save, sender=Result)
def handle_result_update(sender, instance, **kwargs):
    if not instance.pk:
        # Skip new objects (handled by post_save)
        return

    try:
        old_instance = Result.objects.get(pk=instance.pk)
    except Result.DoesNotExist:
        return

    if not instance.trainer or not instance.user:
        return

    if not instance.is_verified:
        logger.info(f"Skipping update for {instance} because result is not verified yet")
        return

    trainer_profile = instance.trainer
    tournament = instance.tournament

    old_rating = int(old_instance.rating)
    new_rating = int(instance.rating)

    if (not old_instance.is_verified and instance.is_verified) or (old_instance.rating != instance.rating):
        logger.info(f"Old rating: {old_rating}, New rating: {new_rating}")
        if old_rating:
            _decrement_trainer_result(trainer_profile.user, tournament, old_rating)
        _increment_trainer_result(trainer_profile.user, tournament, new_rating, instance)


# -----------------------
# Helper Functions
# -----------------------

# -- Increment Trainer Result --
def _increment_trainer_result(trainer_user, tournament, rating, sportsman_result):
    trainer_result, _ = Result.objects.get_or_create(
        user=trainer_user,
        tournament=tournament,
        defaults={
            "country": sportsman_result.country,
            "year": sportsman_result.year,
            "currently_participating": False,
            "rating": 0,
            "gold": 0,
            "silver": 0,
            "bronze": 0,
            "is_verified": True,
            "status": enums.ResultVerificationStatus.VERIFIED.value,
        },
    )
    logger.info(f"Incrementing trainer result for {trainer_user.username} in tournament {tournament.name} with rating {rating}")
    if rating == 1:
        trainer_result.gold += 1
    elif rating == 2:
        trainer_result.silver += 1
    elif rating == 3:
        trainer_result.bronze += 1

    trainer_result.save()

    _calculate_trainer_points(trainer_user)

# -- Decrement Trainer Result --
def _decrement_trainer_result(trainer_user, tournament, rating):
    trainer_result = Result.objects.filter(
        user=trainer_user,
        tournament=tournament,
        currently_participating=False
    ).first()

    if not trainer_result:
        return
    logger.info(f"Decrementing trainer result for {trainer_user.username} in tournament {tournament.name} with rating {rating}")
    if rating == 1 and trainer_result.gold > 0:
        trainer_result.gold -= 1
    elif rating == 2 and trainer_result.silver > 0:
        trainer_result.silver -= 1
    elif rating == 3 and trainer_result.bronze > 0:
        trainer_result.bronze -= 1

    trainer_result.save()

    _calculate_trainer_points(trainer_user)

# -- Calculate Trainer Points --
def _calculate_trainer_points(trainer_user):
    """
    Calculates and updates the trainer's average points based on the tournament and rating.
    """
    qs = trainer_user.trainer_profile.sportsmen.all()
    result = qs.aggregate(total_points=Sum('points'), count=Count('user_id'))

    total_points = result["total_points"] or 0
    count = result["count"] or 0

    trainer_user.trainer_profile.points = (
        total_points / count if count > 0 else 0
    )

    # all_scores = sum(
    #     (s.points or 0) for s in trainer_user.trainer_profile.sportsmen.all()
    # )
    # sportsmans_count = trainer_user.trainer_profile.sportsmen.count()

    # trainer_user.trainer_profile.points = (
    #     all_scores / sportsmans_count if sportsmans_count > 0 else 0
    # )

    trainer_user.trainer_profile.save(update_fields=["points"])


@receiver(pre_delete, sender=Result)
def update_or_delete_trainer_result(sender, instance, **kwargs):
    """
    Runs before deleting a sportsman's result.
    If trainer has other sportsmen in the same tournament → just decrement.
    If not → delete the trainer result entirely.
    """
    if not instance.trainer or not instance.user or not instance.is_verified:
        return  # Skip if no trainer/user or unverified result

    trainer_profile = instance.trainer
    trainer_user = trainer_profile.user
    tournament = instance.tournament
    rating = instance.rating

    # Check if other sportsmen exist for this trainer in the same tournament
    other_sportsman_results = Result.objects.filter(
        trainer=trainer_profile,
        tournament=tournament
    ).exclude(id=instance.id)

    if other_sportsman_results.exists():
        logger.info(f"(pre_delete) Other sportsmen exist → decrementing trainer result...")
        _decrement_trainer_result(trainer_user, tournament, rating)
    else:
        logger.info(f"(pre_delete) No other sportsmen exist → deleting trainer result...")
        Result.objects.filter(
            user=trainer_user,
            tournament=tournament,
            currently_participating=False
        ).delete()
