import astral
import astral.sun
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta, tzinfo
from enum import Enum, auto

from solar_events import *
from format import *


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

MONTHS_IN_SEASON = 3
DAYS_IN_WEEK = 7
DAYS_IN_MONTH = 28

@dataclass
class Day:
    gregorian_date: date
    start: datetime
    end: datetime
    year: int
    season: Season
    month: int | None
    day_of_month: int
    days_since_epoch: int

    @property
    def weekday(self) -> Weekday:
        return Weekday((self.day_of_month + 5) % 7)

    @property
    def day_of_week(self) -> int:
        return ((self.day_of_month + 1) % 7) + 1

    def short_string(self):
        return f"{self.day_of_month:>02}/{self.month_code()}/{self.year:>02}"

    def month_code(self):
        if self.month is None:
            return f"H{self.season.value + 1}"
        else:
            return f"{self.month + MONTHS_IN_SEASON*self.season.value:>02}"

    def month_string(self):
        if self.month is None:
            match self.season:
                case Season.SPRING:
                    return "Summer Solstice Holiday"
                case Season.SUMMER:
                    return "Autumnal Equinox Holiday"
                case Season.AUTUMN:
                    return "Winter Solstice Holiday"
                case Season.WINTER:
                    return "Vernal Equinox Holiday"
        else:
            return ["Early", "Mid", "Late"][self.month - 1] + " " + str(self.season)

    def long_string(self):
        return f"{self.weekday.name.title()} the {ordinal(self.day_of_month)} of {self.month_string()}, Year {self.year}"

    def __str__(self):
        return self.long_string() + " (" + self.short_string() + ")"


@dataclass
class Calendar:
    latitude: float = CANONICAL_LATITUDE
    longitude: float = CANONICAL_LONGITUDE
    timezone: tzinfo | None = None # None for local timezone

    def __post_init__(self):
        self.observer = astral.Observer(self.latitude, self.longitude)
        self.hemisphere = Hemisphere.NORTHERN if self.latitude > 0 else Hemisphere.SOUTHERN
        match self.hemisphere:
            case Hemisphere.SOUTHERN:
                epoch_date = date(2024, 9, 22)
            case Hemisphere.NORTHERN:
                epoch_date = date(2025, 3, 23)
        # fix timezone off-by-ones
        match Weekday(self._start_of_day(epoch_date).weekday()):
            case Weekday.MONDAY:
                epoch_date = epoch_date - timedelta(days=1)
            case Weekday.SATURDAY:
                epoch_date = epoch_date + timedelta(days=1)
        assert Weekday(self._start_of_day(epoch_date).weekday()) == Weekday.SUNDAY
        self.epoch = Day(
            gregorian_date=epoch_date,
            start=self._start_of_day(epoch_date),
            end=self._end_of_day(epoch_date),
            year=1,
            season=Season.SPRING,
            month=1,
            day_of_month=1,
            days_since_epoch=0
        )
        self.days = list(self._calc_days())

    def find_day(self, time: datetime) -> Day | None:
        for day in self.days:
            if day.start <= time < day.end:
                return day
        return None

    def print_block(self, year: int, season: Season, month: int | None, highlight : Day | None = None):
        def is_solar_event_on_day(day):
            for solar_event in SOLAR_EVENTS:
                if day.start <= solar_event.time < day.end:
                    return True
            return False
        WIDTH = 43
        if season == Season.SPRING and month == 1:
            print("")
            print(f"* Year {year} *".center(WIDTH))
            print("")
        day = next(day for day in self.days if day.year == year and day.season == season and day.month == month)
        assert day.day_of_month == 1
        print(f"- {day.month_string()} -".center(WIDTH))
        print("-------------------------------------------")
        print("| Sun | Mon | Tue | Wed | Thu | Fri | Sat |")
        print("-------------------------------------------")
        month = day.month
        while day.month == month:
            week = []
            for _ in range(7):
                day_str = f"{'>' if day == highlight else ' '}{'*' if is_solar_event_on_day(day) else ' '}{day.day_of_month:>2}{'<' if day == highlight else ' '}"
                week.append(day_str)
                day = self.days[day.days_since_epoch + 1]
            print('|' + '|'.join(week) + '|')
        print("-------------------------------------------")
        print("")

    def print(self, year: int, season: Season, month: int | None, highlight : Day | None = None, blocks : int = 16):
        def next_block(year, season, month):
            if month is None:
                if season == Season.WINTER:
                    return (year + 1, Season.SPRING, 1)
                else:
                    return (year, season.next(), 1)
            else:
                return (year, season, month + 1 if month < 3 else None)
        for i in range(blocks):
            self.print_block(year, season, month, highlight)
            (year, season, month) = next_block(year, season, month)

    def _calc_days(self):
        day = self.epoch
        while day is not None:
            yield day
            day = self._next_day(day)

    def _start_of_day(self, date) -> datetime:
        return astral.sun.sunrise(self.observer, date, tzinfo=self.timezone)

    def _end_of_day(self, date) -> datetime:
        return astral.sun.sunrise(self.observer, date + timedelta(days=1), tzinfo=self.timezone)

    def _season_transition_solar_event_type(self, season: Season) -> SolarEventType:
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

    def _find_season_transition_solar_event(self, day: Day) -> SolarEvent | None:
        expected_solar_event_type = self._season_transition_solar_event_type(day.season)
        for solar_event in SOLAR_EVENTS:
            if solar_event.type == expected_solar_event_type and abs(solar_event.time - day.start) <= timedelta(days=120): # check in right year
                return solar_event
        return None

    def _next_day(self, day: Day) -> Day | None:
        gregorian_date = day.gregorian_date + timedelta(days = 1)
        start = self._start_of_day(gregorian_date)
        end = self._end_of_day(gregorian_date)
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
            solar_event = self._find_season_transition_solar_event(day)
            if solar_event is None:
                return None
            assert day.weekday == Weekday.SATURDAY
            leap_week_threshold = self._end_of_day(gregorian_date + timedelta(days=2))
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
            gregorian_date=gregorian_date,
            start=start,
            end=end,
            year=year,
            season=season,
            month=month,
            day_of_month=day_of_month,
            days_since_epoch=day.days_since_epoch + 1,
        )
