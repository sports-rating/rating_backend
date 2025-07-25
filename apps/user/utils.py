from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from apps.shared.utils.logging import logger

def calculate_sportsman_statistics(sportsman):
    """
    Calculate statistics for a sportsman based on their results.
    """
    # Aggregate counts directly in the database
    stats = sportsman.results.aggregate(
        total_gold=Count('id', filter=Q(rating=1)),
        total_silver=Count('id', filter=Q(rating=2)),
        total_bronze=Count('id', filter=Q(rating=3))
    )
    
    return stats

def calculate_trainer_statistics(trainer):
    """
    Calculate statistics for a trainer based on their results and their students' results.
    """
    # Aggregate both trainer's own achievements and students' achievements in a single query
    statistics = trainer.results.aggregate(
        own_total_gold=Coalesce(Count('id', filter=Q(currently_participating=True, rating=1)), Value(0)),
        own_total_silver=Coalesce(Count('id', filter=Q(currently_participating=True, rating=2)), Value(0)),
        own_total_bronze=Coalesce(Count('id', filter=Q(currently_participating=True, rating=3)), Value(0)),
        students_total_gold=Coalesce(Sum('gold', filter=Q(currently_participating=False)), Value(0)),
        students_total_silver=Coalesce(Sum('silver', filter=Q(currently_participating=False)), Value(0)),
        students_total_bronze=Coalesce(Sum('bronze', filter=Q(currently_participating=False)), Value(0)),
    )

    # Combine all statistics
    total_statistics = {
        "gold": statistics["own_total_gold"] + statistics["students_total_gold"],
        "silver": statistics["own_total_silver"] + statistics["students_total_silver"],
        "bronze": statistics["own_total_bronze"] + statistics["students_total_bronze"],
    }

    return {
        "own_statistics": {
            "gold": statistics["own_total_gold"],
            "silver": statistics["own_total_silver"],
            "bronze": statistics["own_total_bronze"],
        },
        "students_statistics": {
            "gold": statistics["students_total_gold"],
            "silver": statistics["students_total_silver"],
            "bronze": statistics["students_total_bronze"],
        },
        "total_statistics": total_statistics,
    }