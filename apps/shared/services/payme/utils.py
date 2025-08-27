from datetime import datetime


def time_to_payme(dt: datetime) -> int:
    if not dt:
        return 0

    return int(dt.timestamp() * 1000)
