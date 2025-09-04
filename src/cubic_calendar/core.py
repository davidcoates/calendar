import astral
import astral.sun
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta, tzinfo
from enum import Enum, auto
from typing import Iterable
import zoneinfo

from .solar_events import *
from .format import *


CANONICAL_LATITUDE = -33.865143
CANONICAL_LONGITUDE = 151.209900
CANONICAL_TIMEZONE = zoneinfo.ZoneInfo("Australia/Sydney")
CANONICAL_EPOCH = date(2024, 9, 22)


class Season(Enum):
    GREENTIDE = 0
    SUNCREST = 1
    EMBERWANE = 2
    FROSTFALL = 3

    def next(self):
        return Season((self.value + 1) % 4)

    def __str__(self):
        return self.name.title()


class Holiday(Enum):
    SUMMER_SOLSTICE = 0
    AUTUMNAL_EQUINOX = 1
    WINTER_SOLSTICE = 2
    VERNAL_EQUINOX = 3

    def __str__(self):
        return self.name.title().replace('_', ' ')


type Block = Season | Holiday


def next_block(block: Block) -> Block:
    if isinstance(block, Holiday):
        return Season((block.value + 1) % 4)
    elif isinstance(block, Season):
        return Holiday(block.value)
    else:
        assert False


class Weekday(Enum):
    SUNDAY = 6
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5

    def __str__(self):
        return self.name.title()


DAYS_IN_WEEK = 7
WEEKS_IN_SEASON = 12
DAYS_IN_SEASON = DAYS_IN_WEEK * WEEKS_IN_SEASON
DAYS_IN_BLOCK = 7
DAYS_IN_LEAP_BLOCK = DAYS_IN_BLOCK * 2

@dataclass
class Day:
    start: datetime
    end: datetime
    year: int
    block: Block
    day_of_block: int
    days_since_epoch: int

    @property
    def weekday(self) -> Weekday:
        return Weekday((self.day_of_block + 5) % 7)

    @property
    def day_of_week(self) -> int:
        return ((self.day_of_block + 1) % 7) + 1

    @property
    def week_of_block(self) -> int:
        return ((self.day_of_block - 1) // 7) + 1

    def human_string(self):
        if isinstance(self.block, Season):
            return f"{self.weekday}, Week {self.week_of_block} of {self.block}, Year {self.year}"
        elif isinstance(self.block, Holiday):
            return f"{self.weekday}, Week {self.week_of_block} of the {self.block} Holiday, Year {self.year}"
        else:
            assert False

    def __str__(self):
        return self.human_string()


@dataclass
class Calendar:
    latitude: float = CANONICAL_LATITUDE
    longitude: float = CANONICAL_LONGITUDE
    timezone: zoneinfo.ZoneInfo = CANONICAL_TIMEZONE

    def __post_init__(self):
        self.observer = astral.Observer(self.latitude, self.longitude)
        self.hemisphere = Hemisphere.NORTHERN if self.latitude > 0 else Hemisphere.SOUTHERN
        self.days = self._calc_days()
        self.epoch = self.days[0]

    def find_day(self, time: datetime) -> Day | None:
        for day in self.days:
            if day.start <= time < day.end:
                return day
        return None

    def _start_of_canonical_day(self, date) -> datetime:
        return astral.sun.sunrise(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date, tzinfo=CANONICAL_TIMEZONE)

    def _end_of_canonical_day(self, date) -> datetime:
        return astral.sun.sunrise(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date + timedelta(days=1), tzinfo=CANONICAL_TIMEZONE)

    def _calc_canonical_days(self) -> Iterable[Day]:
        assert Weekday(self._start_of_canonical_day(CANONICAL_EPOCH).weekday()) == Weekday.SUNDAY
        gregorian_date = CANONICAL_EPOCH
        day = Day(
            start=self._start_of_canonical_day(gregorian_date),
            end=self._end_of_canonical_day(gregorian_date),
            year=1,
            block=Season.GREENTIDE,
            day_of_block=1,
            days_since_epoch=0
        )
        yield day
        while True:
            gregorian_date = gregorian_date + timedelta(days=1)
            start = self._start_of_canonical_day(gregorian_date)
            end = self._end_of_canonical_day(gregorian_date)
            if isinstance(day.block, Holiday) and day.day_of_block == DAYS_IN_BLOCK:
                assert day.weekday == Weekday.SATURDAY
                solar_events = [ solar_event for solar_event in SOLAR_EVENTS if abs(solar_event.time.date() - gregorian_date) <= timedelta(days=14) ]
                if not solar_events:
                    return
                [ solar_event ] = solar_events
                leap_week_threshold = self._end_of_canonical_day(gregorian_date + timedelta(days=2))
                if solar_event.time > leap_week_threshold: # insert a leap week
                    year = day.year
                    block = day.block
                    day_of_block = day.day_of_block + 1
                else:
                    year = day.year + 1 if day.block == Holiday.VERNAL_EQUINOX else day.year
                    block = next_block(day.block)
                    day_of_block = 1
            elif (isinstance(day.block, Holiday) and day.day_of_block == DAYS_IN_LEAP_BLOCK) or \
                 (isinstance(day.block, Season) and day.day_of_block == DAYS_IN_SEASON):
                year = day.year
                block = next_block(day.block)
                day_of_block = 1
            else:
                 year = day.year
                 block = day.block
                 day_of_block = day.day_of_block + 1
            day = Day(
                start=start,
                end=end,
                year=year,
                block=block,
                day_of_block=day_of_block,
                days_since_epoch=day.days_since_epoch + 1,
            )
            yield day

    def _calc_days(self) -> list[Day]:
        days = list(self._calc_canonical_days())
        return list(self._localize(days))

    def _start_of_day(self, date) -> datetime:
        return astral.sun.sunrise(self.observer, date, tzinfo=self.timezone)

    def _end_of_day(self, date) -> datetime:
        return astral.sun.sunrise(self.observer, date + timedelta(days=1), tzinfo=self.timezone)

    def _localize(self, days: list[Day]) -> Iterable[Day]:
        if self.timezone == CANONICAL_TIMEZONE:
            yield from days
            return
        offset = 0
        if self.hemisphere == Hemisphere.NORTHERN:
            offset = next(i for (i, day) in enumerate(days) if day.season == Season.EMBERWANE)
        match Weekday(self._start_of_day(CANONICAL_EPOCH + timedelta(days=offset)).weekday()):
            case Weekday.MONDAY:
                offset -= 1
            case Weekday.SUNDAY:
                pass
            case Weekday.SATURDAY:
                offset += 1
            case _:
                assert False
        gregorian_date = CANONICAL_EPOCH + timedelta(days=offset)
        assert Weekday(self._start_of_day(CANONICAL_EPOCH + timedelta(days=offset)).weekday()) == Weekday.SUNDAY
        assert offset >= 0
        for (i, day) in enumerate(days[offset:]):
            day.start = self._start_of_day(gregorian_date)
            day.end = self._end_of_day(gregorian_date)
            if offset > 0:
                day.year = days[i].year
                day.block = days[i].block
                day.day_of_block = days[i].day_of_block
                day.days_since_epoch = i
            yield day
            gregorian_date = gregorian_date + timedelta(days=1)
