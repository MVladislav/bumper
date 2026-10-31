# Error Codes

Robots report errors as numeric codes. This page documents the codes Bumper
currently maps; unrecognized numeric codes remain visible without an invented
description.

Code meanings can vary by robot family. The sections below group codes by the
component or fault area suggested by their names and available reference data;
they do not imply that every code applies to every robot.

## Robot components

| Code | Name                                  | Description                    |
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

## Appliance components

| Code | Name                                | Description                   |
| ---- | ----------------------------------- | ----------------------------- |
| 201  | `ERROR_AIRFILTERUNISTALL`           | Air filter not installed      |
| 202  | `ERROR_ULTRASONICCOMPONENTABNORMAL` | Ultrasonic component abnormal |
| 203  | `ERROR_SMALLWHEELERROR`             | Small wheel error             |
| 204  | `ERROR_WHEEL_HANG`                  | Wheel hang                    |
| 205  | `ERROR_ION_STERILIZE_EXHAUSTED`     | Ion sterilize exhausted       |
| 206  | `ERROR_ION_STERILIZE_ABNORMAL`      | Ion sterilize abnormal        |
| 207  | `ERROR_ION_STERILIZE_FAULT`         | Ion sterilize fault           |
| 209  | `ERROR_DTOF_ABNORMAL`               | dToF sensor abnormal          |

## Mop station

| Code | Name                           | Description                           |
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

## Base station

| Code | Name                                    | Description                                        |
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

## GOAT mower

| Code | Name                             | Description              |
| ---- | -------------------------------- | ------------------------ |
| 401  | `ERROR_TILT`                     | Tilt                     |
| 402  | `ERROR_OVERHANG`                 | Overhang                 |
| 403  | `ERROR_SENSOR`                   | Sensor                   |
| 404  | `ERROR_BATTERY`                  | Battery                  |
| 405  | `ERROR_LEFT_DRIVING_WHEEL`       | Left driving wheel       |
| 406  | `ERROR_ROTATION_CUTTER_HEAD`     | Rotation cutter head     |
| 407  | `ERROR_BUMP_PLATE`               | Bump plate               |
| 408  | `ERROR_TO_ERASE`                 | To erase                 |
| 409  | `ERROR_CLEAN_LENS`               | Clean lens               |
| 410  | `ERROR_GET_LOST`                 | Get lost                 |
| 411  | `ERROR_STATION_LOCATION`         | Station location         |
| 412  | `ERROR_BEACON_LOCATION`          | Beacon location          |
| 414  | `ERROR_RGBD_DIRTY`               | RGBD dirty               |
| 415  | `ERROR_PANORAMIC_CAMEAR_DIRTY`   | Panoramic camera dirty   |
| 416  | `ERROR_BATTERY_HIGH_TEMPERATURE` | Battery high temperature |
| 417  | `ERROR_BATTERY_LOW_TEMPERATURE`  | Battery low temperature  |
| 418  | `ERROR_IN_FORBIDDEN_AREA`        | In forbidden area        |
| 420  | `ERROR_OUT_OF_MAP_RANGE`         | Out of map range         |
| 421  | `ERROR_BEACON_SINGAL`            | Beacon signal            |
| 422  | `ERROR_GPS_SIGNAL_WEAK_BACK`     | GPS signal weak back     |
| 423  | `ERROR_GPS_SIGNAL_WEAK_WAIT`     | GPS signal weak wait     |
| 424  | `ERROR_RIGHT_DRIVING_WHEEL`      | Right driving wheel      |
| 430  | `ERROR_SENSOR430`                | Sensor 430               |
| 431  | `ERROR_SENSOR431`                | Sensor 431               |
| 432  | `ERROR_SENSOR432`                | Sensor 432               |
| 433  | `ERROR_SENSOR433`                | Sensor 433               |
| 434  | `ERROR_SENSOR434`                | Sensor 434               |
| 435  | `ERROR_SENSOR435`                | Sensor 435               |
| 520  | `ERROR_TRAPPED`                  | Trapped                  |

## Camera and vision

| Code | Name                           | Description                       |
| ---- | ------------------------------ | --------------------------------- |
| 601  | `ERROR_ClosedAIVISideAbnormal` | Closed AI vision: side abnormal   |
| 602  | `ERROR_ClosedAIVIRollAbnormal` | Closed AI vision: roller abnormal |

## Code reference

The mapping is maintained in `bumper/utils/device_errors.py`:

```python
from bumper.utils.device_errors import describe

describe(312)
```

This returns `Auto empty station: dust bag full (312)`. The app-compatible
`api/pim/eventdetail.html?errcode=...` page uses the same mapping. Guidance is
curated for some codes; other codes receive safe, general recommendations that
are identified as generic rather than official Ecovacs instructions.
