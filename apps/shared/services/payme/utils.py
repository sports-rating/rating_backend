from datetime import datetime


def time_to_payme(dt: datetime) -> int:
    """
    Convert datetime object to Payme's datetime format.
    """
    if not dt:
        return 0

    return int(dt.timestamp() * 1000)


def time_to_service(milliseconds: int) -> datetime:
    """
    Converts milliseconds since the epoch to a datetime object.
    """
    return datetime.fromtimestamp(milliseconds / 1000)
