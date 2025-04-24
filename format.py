from datetime import datetime

TIME_FORMAT = "%d/%m/%Y %H:%M"

def format_time(time: datetime):
    return time.astimezone().strftime(TIME_FORMAT)

