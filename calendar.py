import astral
import astral.sun
import zoneinfo
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta, tzinfo
from enum import Enum, auto

from solar_events import *
from format import *


CANONICAL_LATITUDE = -33.865143
CANONICAL_LONGITUDE = 151.209900
CANONICAL_TIMEZONE = zoneinfo.ZoneInfo("Australia/Sydney")
CANONICAL_EPOCH = date(2024, 9, 22)

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

class Block(Enum):
    EARLY = 0
    MIDDLE = 1
    LATE = 2
    HOLIDAY = 3

    def next(self):
        return Block((self.value + 1) % 4)

    def human_string(self, season: Season):
        if self == Block.HOLIDAY:
            match season:
                case Season.SPRING:
                    return "Summer Solstice Holiday"
                case Season.SUMMER:
                    return "Autumnal Equinox Holiday"
                case Season.AUTUMN:
                    return "Winter Solstice Holiday"
                case Season.WINTER:
                    return "Vernal Equinox Holiday"
        else:
            return ["Early", "Mid", "Late"][self.value] + " " + str(season)


DAYS_IN_WEEK = 7
DAYS_IN_MONTH = 28

@dataclass
class Day:
    start: datetime
    end: datetime
    year: int
    season: Season
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
    def block_of_year(self) -> int:
        return 4*self.season.value + self.block.value + 1

    def code_string(self):
        return f"{self.year:>03}-{self.block_of_year}-{self.day_of_block:>02}"

    def human_string(self):
        return f"{self.weekday.name.title()} the {ordinal(self.day_of_block)} of {self.block.human_string(self.season)}, Year {self.year}"

    def __str__(self):
        return self.human_string() + " (" + self.code_string() + ")"


@dataclass
class Calendar:
    latitude: float
    longitude: float
    timezone: tzinfo

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

    def print_block(self, year: int, season: Season, block: Block, highlight : Day | None = None):
        def is_solar_event_on_day(day):
            for solar_event in SOLAR_EVENTS:
                if day.start <= solar_event.time < day.end:
                    return True
            return False
        WIDTH = 43
        if season == Season.SPRING and block == Block.EARLY:
            print("")
            print(f"* Year {year} *".center(WIDTH))
            print("")
        day = next(day for day in self.days if day.year == year and day.season == season and day.block == block)
        assert day.day_of_block == 1
        print(f"- {day.block.human_string(season)} -".center(WIDTH))
        print("-------------------------------------------")
        print("| Sun | Mon | Tue | Wed | Thu | Fri | Sat |")
        print("-------------------------------------------")
        block = day.block
        while day.block == block:
            week = []
            for _ in range(7):
                day_str = f"{'>' if day == highlight else ' '}{'*' if is_solar_event_on_day(day) else ' '}{day.day_of_block:>2}{'<' if day == highlight else ' '}"
                week.append(day_str)
                day = self.days[day.days_since_epoch + 1]
            print('|' + '|'.join(week) + '|')
        print("-------------------------------------------")
        print("")

    def print(self, year: int, season: Season, block: Block, highlight : Day | None = None, blocks : int = 16):
        def next_block(year, season, block):
            if block == Block.HOLIDAY:
                if season == Season.WINTER:
                    year = year + 1
                season = season.next()
            return (year, season, block.next())
        for i in range(blocks):
            self.print_block(year, season, block, highlight)
            (year, season, block) = next_block(year, season, block)

    def _start_of_canonical_day(self, date) -> datetime:
        return astral.sun.sunrise(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date, tzinfo=CANONICAL_TIMEZONE)

    def _end_of_canonical_day(self, date) -> datetime:
        return astral.sun.sunrise(astral.Observer(CANONICAL_LATITUDE, CANONICAL_LONGITUDE), date + timedelta(days=1), tzinfo=CANONICAL_TIMEZONE)

    def _calc_canonical_days(self):
        assert Weekday(self._start_of_canonical_day(CANONICAL_EPOCH).weekday()) == Weekday.SUNDAY
        gregorian_date = CANONICAL_EPOCH
        day = Day(
            start=self._start_of_canonical_day(gregorian_date),
            end=self._end_of_canonical_day(gregorian_date),
            year=1,
            season=Season.SPRING,
            block=Block.EARLY,
            day_of_block=1,
            days_since_epoch=0
        )
        yield day
        while True:
            gregorian_date = gregorian_date + timedelta(days=1)
            start = self._start_of_canonical_day(gregorian_date)
            end = self._end_of_canonical_day(gregorian_date)
            if day.block != Block.HOLIDAY and not (day.block == Block.LATE and day.day_of_block == DAYS_IN_MONTH):
                year = day.year
                season = day.season
                block = day.block.next() if day.day_of_block == DAYS_IN_MONTH else day.block
                day_of_block = (day.day_of_block % DAYS_IN_MONTH) + 1
            elif day.block != Block.HOLIDAY: # transition to holiday
                year = day.year
                season = day.season
                day_of_block = 1
                block = Block.HOLIDAY
            elif day.day_of_block % DAYS_IN_WEEK != 0:
                 year = day.year
                 season = day.season
                 day_of_block = day.day_of_block + 1
                 block = Block.HOLIDAY
            else:
                assert day.weekday == Weekday.SATURDAY
                solar_events = [ solar_event for solar_event in SOLAR_EVENTS if abs(solar_event.time.date() - gregorian_date) <= timedelta(days=14) ]
                if not solar_events:
                    return
                [ solar_event ] = solar_events
                leap_week_threshold = self._end_of_canonical_day(gregorian_date + timedelta(days=2))
                if solar_event.time > leap_week_threshold: # insert a leap week
                    year = day.year
                    season = day.season
                    day_of_block = day.day_of_block + 1
                    block = Block.HOLIDAY
                else:
                    year = day.year + 1 if day.season == Season.WINTER else day.year
                    season = day.season.next()
                    day_of_block = 1
                    block = Block.EARLY
            day = Day(
                start=start,
                end=end,
                year=year,
                season=season,
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

    def _localize(self, days):
        offset = 0
        if self.hemisphere == Hemisphere.NORTHERN:
            offset = next(i for (i, day) in enumerate(days) if day.season == Season.AUTUMN)
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
                day.season = days[i].season
                day.block = days[i].block
                day.day_of_block = days[i].day_of_block
                day.days_since_epoch = i
            yield day
            gregorian_date = gregorian_date + timedelta(days=1)
