import astral
import astral.sun
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from enum import Enum, auto

from solar_events import *


CANONICAL_LATITUDE = -33.865143
CANONICAL_LONGITUDE = 151.209900


class Season(Enum):
    SPRING = 0
    SUMMER = 1
    AUTUMN = 2
    WINTER = 3

    def next(self):
        return Season((self.value + 1) % 4)

    def __str__(self):
        return self.name.title()


class Weekday(Enum):
    SUNDAY = 6
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5


def ordinal(n: int):
    suffix = "th" if 11 <= (n % 100) <= 13 else ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    return f"{n}{suffix}"


@dataclass
class Day:
    start: datetime
    end: datetime
    year: int
    season: Season
    month: int | None
    day_of_month: int

    @property
    def date(self) -> date:
        return date(self.start.year, self.start.month, self.start.day)

    @property
    def weekday(self) -> Weekday:
        return Weekday((self.day_of_month + 5) % 7)

    @property
    def day_of_week(self) -> int:
        return ((self.day_of_month + 1) % 7) + 1

    def short_string(self):
        month = self.month or 'H'
        return f"{self.day_of_month:>02}/{month}/{self.season}/{self.year:>02}"

    def month_string(self):
        if self.month is None:
            return f"{self.season} Holiday"
        else:
            return ["Early", "Mid", "Late"][self.month - 1] + " " + str(self.season)

    def long_string(self):
        return f"{self.weekday.name.title()} the {ordinal(self.day_of_month)} of {self.month_string()}, Year {self.year}"

    def __str__(self):
        return self.long_string()


MONTHS_IN_SEASON = 3
DAYS_IN_WEEK = 7
DAYS_IN_MONTH = 28

@dataclass
class Calendar:
    latitude: float = CANONICAL_LATITUDE
    longitude: float = CANONICAL_LONGITUDE

    def __post_init__(self):
        self.observer = astral.Observer(self.latitude, self.longitude)
        self.hemisphere = Hemisphere.NORTHERN if self.latitude > 0 else Hemisphere.SOUTHERN
        match self.hemisphere:
            case Hemisphere.SOUTHERN:
                epoch_date = date(2024, 9, 22)
            case Hemisphere.NORTHERN:
                epoch_date = date(2025, 3, 23)
        if Weekday(self.start_of_day(epoch_date).astimezone().weekday()) == Weekday.MONDAY: # fix timezone off-by-one
            epoch_date = epoch_date - timedelta(days=1)
        assert Weekday(self.start_of_day(epoch_date).astimezone().weekday()) == Weekday.SUNDAY
        self.epoch = Day(
            start=self.start_of_day(epoch_date),
            end=self.end_of_day(epoch_date),
            year=1,
            season=Season.SPRING,
            month=1,
            day_of_month=1,
        )

    def start_of_day(self, date) -> datetime:
        return astral.sun.sunrise(self.observer, date)

    def end_of_day(self, date) -> datetime:
        return astral.sun.sunrise(self.observer, date + timedelta(days=1))

    def season_transition_solar_event_type(self, season: Season) -> SolarEventType:
        match self.hemisphere:
            case Hemisphere.NORTHERN:
                match season:
                    case Season.SPRING:
                        return SolarEventType.JUNE_SOLSTICE
                    case Season.SUMMER:
                        return SolarEventType.SEPTEMBER_EQUINOX
                    case Season.AUTUMN:
                        return SolarEventType.DECEMBER_SOLSTICE
                    case Season.WINTER:
                        return SolarEventType.MARCH_EQUINOX
            case Hemisphere.SOUTHERN:
                match season:
                    case Season.SPRING:
                        return SolarEventType.DECEMBER_SOLSTICE
                    case Season.SUMMER:
                        return SolarEventType.MARCH_EQUINOX
                    case Season.AUTUMN:
                        return SolarEventType.JUNE_SOLSTICE
                    case Season.WINTER:
                        return SolarEventType.SEPTEMBER_EQUINOX

    def find_season_transition_solar_event(self, day: Day) -> SolarEvent | None:
        expected_solar_event_type = self.season_transition_solar_event_type(day.season)
        for solar_event in SOLAR_EVENTS:
            if solar_event.type == expected_solar_event_type and abs(solar_event.time - day.start) <= timedelta(days=120): # check in right year
                return solar_event
        return None

    def is_solar_event_on_day(self, day: Day) -> bool:
        solar_event = self.find_season_transition_solar_event(day)
        if solar_event is None:
            return False
        else:
            return day.start <= solar_event.time < day.end

    def next_day(self, day: Day) -> Day | None:
        date = day.date + timedelta(days=1)
        start = self.start_of_day(date)
        end = self.end_of_day(date)
        if day.month is not None and not (day.month == MONTHS_IN_SEASON and day.day_of_month == DAYS_IN_MONTH):
            year = day.year
            season = day.season
            month = day.month + 1 if day.day_of_month == DAYS_IN_MONTH else day.month
            day_of_month = (day.day_of_month % DAYS_IN_MONTH) + 1
        elif day.month is not None: # transition to holiday
            year = day.year
            season = day.season
            day_of_month = 1
            month = None
        elif day.day_of_month % DAYS_IN_WEEK != 0:
             year = day.year
             season = day.season
             day_of_month = day.day_of_month + 1
             month = None
        else:
            solar_event = self.find_season_transition_solar_event(day)
            if solar_event is None:
                return None
            assert day.weekday == Weekday.SATURDAY
            leap_week_threshold = self.end_of_day(day.date + timedelta(days=2))
            if solar_event.time > leap_week_threshold: # insert a leap week
                year = day.year
                season = day.season
                day_of_month = day.day_of_month + 1
                month = None
            else:
                year = day.year + 1 if day.season == Season.WINTER else day.year
                season = day.season.next()
                day_of_month = 1
                month = 1
        return Day(
            start=start,
            end=end,
            year=year,
            season=season,
            month=month,
            day_of_month=day_of_month,
        )

    def next_day_or_fail(self, day: Day) -> Day:
        next_day = self.next_day(day)
        if next_day is None:
            assert False
        return next_day

    def days(self):
        day = self.epoch
        while day is not None:
            yield day
            day = self.next_day(day)

    def today(self) -> Day:
        today = datetime.now(tz=timezone.utc)
        for day in self.days():
            if day.start <= today < day.end:
                return day
        assert False

    def print_from(self, day: Day):

        def is_solar_event_on_day(day):
            for solar_event in SOLAR_EVENTS:
                if day.start <= solar_event.time < day.end:
                    return True
            return False

        def day_of_month_string(day):
            if is_solar_event_on_day(day):
                return f" *{day.day_of_month:>2} "
            else:
                return f"  {day.day_of_month:>2} "

        WIDTH = 43
        def print_month(day):
            if day.season == Season.SPRING and day.month == 1:
                print("")
                print(f"* Year {day.year} *".center(WIDTH))
                print("")
            if day.day_of_month != 1:
                day = next(back for back in self.days() if back.year == day.year and back.season == day.season and back.month == day.month)
            assert day.day_of_month == 1
            print(f"- {day.month_string()} -".center(WIDTH))
            print("-------------------------------------------")
            print("| Sun | Mon | Tue | Wed | Thu | Fri | Sat |")
            print("-------------------------------------------")
            month = day.month
            while day.month == month:
                week = []
                for _ in range(7):
                    week.append(day_of_month_string(day))
                    day = self.next_day_or_fail(day)
                print('|' + '|'.join(week) + '|')
            print("")
            return day

        end_year = day.year + 1
        end_season = day.season
        end_month = day.month
        while not (day.year == end_year and day.season == end_season and day.month == end_month):
            day = print_month(day)
