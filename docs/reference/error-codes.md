# Error Codes

The robot reports the error it runs into with a number. This page lists every
number the robot uses and what it means, so the numbers in Home Assistant or in
the app can be read.

The numbers come from the robot data the official app carries around, and the
names are the ones the app uses.

## The unit itself

| Code | Name                                  | Meaning                        |
| ---- | ------------------------------------- | ------------------------------ |
| 0    | `ERROR_NO`                            | No error                       |
| 101  | `ERROR_BATTERY_LOW`                   | Battery low                    |
| 102  | `ERROR_HANG`                          | The unit hangs                 |
| 103  | `ERROR_WHEEL`                         | Wheel abnormal                 |
| 104  | `ERROR_DOWNSENSORABNORMAL`            | Down sensor abnormal           |
| 105  | `ERROR_STUCK`                         | Stuck                          |
| 106  | `ERROR_SIDEBRUSHEXHAUSTED`            | Side brush exhausted           |
| 107  | `ERROR_DUSTCASEHEAPEXHAUSTED`         | Dust case exhausted            |
| 108  | `ERROR_SIDEABNORMAL`                  | Side brush abnormal            |
| 109  | `ERROR_ROLLABNORMAL`                  | Roller abnormal                |
| 110  | `ERROR_NODUSTBOX`                     | No dust box                    |
| 111  | `ERROR_BUMPABNORMAL`                  | Bumper abnormal                |
| 112  | `ERROR_LDSABNORMAL`                   | Laser distance sensor abnormal |
| 113  | `ERROR_MAINBRUSHEXHAUSTED`            | Main brush exhausted           |
| 114  | `ERROR_DUSTCASEEXHAUSTED`             | Dust case filled               |
| 115  | `ERROR_BATTERYERROR`                  | Battery error                  |
| 116  | `ERROR_FORWARDLOOKINGERROR`           | Forward looking sensor error   |
| 117  | `ERROR_GYROSCOPEERROR`                | Gyroscope error                |
| 118  | `ERROR_STRAINERBLOCK`                 | Strainer blocked               |
| 119  | `ERROR_FANERROR`                      | Fan error                      |
| 120  | `ERROR_WATERBOX_ERROR`                | Water box error                |
| 121  | `ERROR_PLATE_JAMMED`                  | Plate jammed                   |
| 125  | `ERROR_HARDWIPE_TANK_MACHINERY_ERROR` | Hard wipe tank machinery error |
| 126  | `ERROR_NO_HARDWIPE_TANK`              | No hard wipe tank              |
| 127  | `ERROR_NO_HARDWIPE_BRUSH`             | No hard wipe brush             |
| 128  | `ERROR_SET_HARDWIPE_BRUSH`            | Hard wipe brush not set        |
| 129  | `ERROR_BIND_HARDWIPE_BRUSH`           | Hard wipe brush not bound      |

## The air treatment

| Code | Name                                | Meaning                       |
| ---- | ----------------------------------- | ----------------------------- |
| 201  | `ERROR_AIRFILTERUNISTALL`           | Air filter not installed      |
| 202  | `ERROR_ULTRASONICCOMPONENTABNORMAL` | Ultrasonic component abnormal |
| 203  | `ERROR_SMALLWHEELERROR`             | Small wheel error             |
| 204  | `ERROR_WHEEL_HANG`                  | Wheel hang                    |
| 205  | `ERROR_ION_STERILIZE_EXHAUSTED`     | Ion sterilize exhausted       |
| 206  | `ERROR_ION_STERILIZE_ABNORMAL`      | Ion sterilize abnormal        |
| 207  | `ERROR_ION_STERILIZE_FAULT`         | Ion sterilize fault           |
| 209  | `ERROR_DTOF_ABNORMAL`               | dToF sensor abnormal          |

## The mop station

| Code | Name                           | Meaning                               |
| ---- | ------------------------------ | ------------------------------------- |
| 301  | `ERROR_MCD_NO_CLEANWATER`      | Mop station: no clean water           |
| 302  | `ERROR_MCD_FULL_DIRTYWATER`    | Mop station: dirty water full         |
| 303  | `ERROR_MCD_NO_CLEANWATER_TANK` | Mop station: no clean water tank      |
| 304  | `ERROR_MCD_NO_DIRTYWATER_TANK` | Mop station: no dirty water tank      |
| 305  | `ERROR_MCD_CLEANTANK_ERROR`    | Mop station: clean tank error         |
| 306  | `ERROR_MCD_NO_CLEANTANK_WEB`   | Mop station: clean tank not connected |
| 307  | `ERROR_MCD_MACHINERY_ERROR`    | Mop station: machinery error          |
| 308  | `ERROR_MCD_CONNECTION_ERROR`   | Mop station: connection error         |
| 309  | `ERROR_TANK_TOOHOT_ERROR`      | Water tank too hot                    |

## The base station

| Code | Name                                    | Meaning                                            |
| ---- | --------------------------------------- | -------------------------------------------------- |
| 310  | `ERROR_AUTO_EMPTY_OPEN`                 | Auto empty station: lid open                       |
| 311  | `ERROR_AUTO_EMPTY_UNINSTALL`            | Auto empty station: not installed                  |
| 312  | `ERROR_AUTO_EMPTY_FULL`                 | Auto empty station: dust bag full                  |
| 313  | `ERROR_AUTO_EMPTY_UNKNOWN`              | Auto empty station: unknown error                  |
| 314  | `ERROR_BASE_STATION_WATER_UNINSTALL`    | Base station: water filter not installed           |
| 315  | `ERROR_BASE_STATION_SILVER_UNINSTALL`   | Base station: silver module not installed          |
| 316  | `ERROR_BASE_STATION_FULL_UNINSTALL`     | Base station: dust bag not installed               |
| 317  | `ERROR_BASE_STATION_UD_WATER_UNINSTALL` | Base station: undiluted water module not installed |
| 318  | `ERROR_BASE_STATION_UD_WATER_FULL`      | Base station: undiluted water full                 |
| 319  | `ERROR_BASE_STATION_CLEAN_WATER_EMPTY`  | Base station: clean water empty                    |

## The camera

| Code | Name                           | Meaning                           |
| ---- | ------------------------------ | --------------------------------- |
| 601  | `ERROR_ClosedAIVISideAbnormal` | Closed AI vision: side abnormal   |
| 602  | `ERROR_ClosedAIVIRollAbnormal` | Closed AI vision: roller abnormal |

## In the code

The mapping lives in `bumper/utils/device_errors.py`:

```python
from bumper.utils.device_errors import describe

describe(312)
```

returns `Auto empty station: dust bag full (312)`.
