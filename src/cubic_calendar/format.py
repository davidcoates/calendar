from datetime import datetime

TIME_FORMAT = "%d/%m/%Y %H:%M"

def format_time(time: datetime):
    return time.astimezone().strftime(TIME_FORMAT)

def ordinal(n: int):
    suffix = "th" if 11 <= (n % 100) <= 13 else ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    return f"{n}{suffix}"
