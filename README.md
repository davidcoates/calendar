# Dave's Cubic Seasonal Calendar

A solar calendar based around the astronomical seasons.

## Rules

* The year is broken up by the four seasons: spring, summer, autumn, winter.
* Every season contains three months of four weeks, with an extra holiday period at the end of the season to mark the solstice / equinox.
* Every week starts at sunrise on Sunday.
* Every year starts on Sunday the 1st of spring.
* Every holiday period is either one week or two weeks, the latter being in the case of a leap week.
* A leap week is inserted if the solstice / equinox would otherwise fall after sunset of the first Monday of the next season.
* The epoch (year 1) begins on the first Sunday after the spring equinox of 2024 (Southern Hemisphere) or 2025 (Northern Hemisphere).

## Benefits

* Proper alignment with the astrological seasons.
* For any date, its day of the week is the same every year.
* A season of 12 working weeks is ideal for long term routines (e.g. work, or an exercise program). It can be split into three blocks of four months, or four blocks of three months, or two blocks of six weeks, etc.
* Leap weeks provide a convenient opportunity for an extended holiday, e.g. an international trip.
* The year is a cube:
  - Each working week is a symmetry of the cube (48 weeks = 48 symmetries).
  - Each month is an edge of the cube (12 months = 12 edges).

## Setup

Running `main.py` produces a print out of the current date, and a calendar of twelve months from the current month. Solstices and equinoxes are marked with an asterisk.

The default location is Sydney, Australia. Custom latitude and longitude can be specified as arguments to the `Calendar` class.
