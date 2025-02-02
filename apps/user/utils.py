def calculate_sportsman_statistics(sportsman):
    """
    Calculate statistics for a sportsman based on their results.
    """
    total_gold = sportsman.results.filter(rating=1).count()
    total_silver = sportsman.results.filter(rating=2).count()
    total_bronze = sportsman.results.filter(rating=3).count()

    return {
        "total_gold": total_gold,
        "total_silver": total_silver,
        "total_bronze": total_bronze,
    }


def calculate_trainer_statistics(trainer):
    """
    Calculate statistics for a trainer based on their results and their students' results.
    """
    own_total_gold = 0
    own_total_silver = 0
    own_total_bronze = 0

    students_total_gold = 0
    students_total_silver = 0
    students_total_bronze = 0

    trainer_results = trainer.trainer_results.all()

    for result in trainer_results:
        if result.currently_participating:
            # Trainer is participating as a sportsman
            if result.rating == 1:
                own_total_gold += 1
            elif result.rating == 2:
                own_total_silver += 1
            elif result.rating == 3:
                own_total_bronze += 1
        else:
            # Trainer is participating as a trainer: calculate based on students' achievements
            students_total_gold += result.number_of_gold or 0
            students_total_silver += result.number_of_silver or 0
            students_total_bronze += result.number_of_bronze or 0

    total_gold = own_total_gold + students_total_gold
    total_silver = own_total_silver + students_total_silver
    total_bronze = own_total_bronze + students_total_bronze

    return {
        "own_statistics": {
            "gold": own_total_gold,
            "silver": own_total_silver,
            "bronze": own_total_bronze,
        },
        "students_statistics": {
            "gold": students_total_gold,
            "silver": students_total_silver,
            "bronze": students_total_bronze,
        },
        "total_statistics": {
            "gold": total_gold,
            "silver": total_silver,
            "bronze": total_bronze,
        },
    }
