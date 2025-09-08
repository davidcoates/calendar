import argparse
import zoneinfo
import sys
from datetime import datetime, timezone

from .core import *
from .solar_events import SOLAR_EVENTS


def print_block(calendar: Calendar, year: int, block: Block, highlight : Day | None = None):
    def is_solar_event_on_day(day):
        for solar_event in SOLAR_EVENTS:
            if day.start <= solar_event.time < day.end:
                return True
        return False
    WIDTH = 43
    if block == Season.GREENTIDE:
        print("")
        print(f"* Year {year} *".center(WIDTH))
        print("")
    day = next(day for day in calendar.days if day.year == year and day.block == block)
    assert day.day_of_block == 0
    print(f"- {day.block} -".center(WIDTH))
    print("--------------------------------------------------")
    print("| Week | Sun | Mon | Tue | Wed | Thu | Fri | Sat |")
    print("--------------------------------------------------")
    block = day.block
    while day.block == block:
        week = [f"  {day.week:>2}  "]
        for _ in range(7):
            if day == highlight:
                day_str = "TODAY"
            elif is_solar_event_on_day(day):
                day_str = "SOLAR"
            else:
                day_str = "     "
            week.append(day_str)
            day = calendar.days[day.days_since_epoch + 1]
        print('|' + '|'.join(week) + '|')
    print("--------------------------------------------------")
    print("")


def print_calendar(calendar: Calendar, year: int, block: Block, blocks: int, highlight : Day | None = None):
    for _ in range(blocks):
        print_block(calendar, year, block, highlight)
        if block == Holiday.VERNAL_EQUINOX:
            year = year + 1
        block = block.next()


def main():

    parser = argparse.ArgumentParser(description="Dave's Cubic Solar Calendar")

    local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
    parser.add_argument("--latitude", type=float, default=CANONICAL_LATITUDE, help="used to derive sunrise/sunset times (default is that of Sydney, Australia)")
    parser.add_argument("--longitude", type=float, default=CANONICAL_LONGITUDE, help="used to derive sunrise/sunset times (default is that of Sydney, Australia)")
    parser.add_argument("--timezone", type=str, default=None, metavar='TIMEZONE', choices=zoneinfo.available_timezones(), help=f"used when displaying times (default is the system local timezone = {local_timezone})")
    parser.add_argument("-t", "--time", type=str, default=None, help="display the date at the described timepoint (in isoformat), not 'now'")
    subparsers = parser.add_subparsers(dest="command")

    parser_calendar = subparsers.add_parser("calendar", help="display a calendar, with '*' denoting a solstice/equinox")
    parser_calendar.add_argument('--blocks', type=int, default=3, help="the number of blocks (months or holidays) to display")

    args = parser.parse_args()

    if args.timezone is None:
        args.timezone = local_timezone
    else:
        args.timezone = zoneinfo.ZoneInfo(args.timezone)

    calendar = Calendar(args.latitude, args.longitude, args.timezone)

    gregorian_date = datetime.fromisoformat(args.time) if args.time is not None else datetime.now()
    if gregorian_date.tzinfo is None:
        gregorian_date = gregorian_date.astimezone(args.timezone)

    cubic_date = calendar.find_day(gregorian_date)
    if cubic_date is None:
        print(f"failed to convert time({args.time}) to date", file=sys.stderr)
        return

    if args.time is None:
        print(f"It is now {cubic_date}.")
    else:
        print(f"{gregorian_date} is {cubic_date}.")

    print("")
    print(f"The day begins at {cubic_date.start} and ends at {cubic_date.end}.")

    if args.command == "calendar":
        print("")
        print_calendar(calendar, cubic_date.year, cubic_date.block, args.blocks, highlight=cubic_date)


if __name__ == "__main__":
    main()
