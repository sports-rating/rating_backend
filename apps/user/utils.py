from django.db.models import Count, Q, Sum
from shared.addons.custom_logging import logger

def calculate_sportsman_statistics(sportsman):
    """
    Calculate statistics for a sportsman based on their results.
    """
    result_counts = (
        sportsman.results
        .values('rating')
        .annotate(count=Count('id'))
    )
    logger.info(f"{result_counts}")

    # Initialize counts
    stats = {"total_gold": 0, "total_silver": 0, "total_bronze": 0}
    
    # Map result counts to the corresponding keys
    for result in result_counts:
        if result['rating'] == 1:
            stats["total_gold"] = result['count']
        elif result['rating'] == 2:
            stats["total_silver"] = result['count']
        elif result['rating'] == 3:
            stats["total_bronze"] = result['count']
    
    return stats


def calculate_trainer_statistics(trainer):
    """
    Calculate statistics for a trainer based on their results and their students' results.
    """
    # Calculate trainer's own achievements
    own_statistics = trainer.results.filter(currently_participating=True).aggregate(
        own_total_gold=Count('id', filter=Q(rating=1)),
        own_total_silver=Count('id', filter=Q(rating=2)),
        own_total_bronze=Count('id', filter=Q(rating=3)),
    )
    
    # Calculate students' achievements (total gold, silver, bronze from their results)
    students_statistics = trainer.results.filter(currently_participating=False).aggregate(
        students_total_gold=Sum('gold', default=0),
        students_total_silver=Sum('silver', default=0),
        students_total_bronze=Sum('bronze', default=0),
    )

    # Combine all statistics
    total_statistics = {
        "gold": own_statistics["own_total_gold"] + students_statistics["students_total_gold"],
        "silver": own_statistics["own_total_silver"] + students_statistics["students_total_silver"],
        "bronze": own_statistics["own_total_bronze"] + students_statistics["students_total_bronze"],
    }

    return {
        "own_statistics": {
            "gold": own_statistics["own_total_gold"],
            "silver": own_statistics["own_total_silver"],
            "bronze": own_statistics["own_total_bronze"],
        },
        "students_statistics": {
            "gold": students_statistics["students_total_gold"],
            "silver": students_statistics["students_total_silver"],
            "bronze": students_statistics["students_total_bronze"],
        },
        "total_statistics": total_statistics,
    }