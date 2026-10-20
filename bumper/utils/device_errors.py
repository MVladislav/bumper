"""The error codes the robot reports and what they mean.

The robot reports the error it runs into with a number. The app turns that
number into a name and a text, and the numbers come from the robot data the
app carries around.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceError:
    """An error the robot can report."""

    code: int
    name: str
    description: str


# The errors the robot reports, in the order of their number.
DEVICE_ERRORS: tuple[DeviceError, ...] = (
    DeviceError(0, "ERROR_NO", "No error"),
    DeviceError(101, "ERROR_BATTERY_LOW", "Battery low"),
    DeviceError(102, "ERROR_HANG", "The unit hangs"),
    DeviceError(103, "ERROR_WHEEL", "Wheel abnormal"),
    DeviceError(104, "ERROR_DOWNSENSORABNORMAL", "Down sensor abnormal"),
    DeviceError(105, "ERROR_STUCK", "Stuck"),
    DeviceError(106, "ERROR_SIDEBRUSHEXHAUSTED", "Side brush exhausted"),
    DeviceError(107, "ERROR_DUSTCASEHEAPEXHAUSTED", "Dust case exhausted"),
    DeviceError(108, "ERROR_SIDEABNORMAL", "Side brush abnormal"),
    DeviceError(109, "ERROR_ROLLABNORMAL", "Roller abnormal"),
    DeviceError(110, "ERROR_NODUSTBOX", "No dust box"),
    DeviceError(111, "ERROR_BUMPABNORMAL", "Bumper abnormal"),
    DeviceError(112, "ERROR_LDSABNORMAL", "Laser distance sensor abnormal"),
    DeviceError(113, "ERROR_MAINBRUSHEXHAUSTED", "Main brush exhausted"),
    DeviceError(114, "ERROR_DUSTCASEEXHAUSTED", "Dust case filled"),
    DeviceError(115, "ERROR_BATTERYERROR", "Battery error"),
    DeviceError(116, "ERROR_FORWARDLOOKINGERROR", "Forward looking sensor error"),
    DeviceError(117, "ERROR_GYROSCOPEERROR", "Gyroscope error"),
    DeviceError(118, "ERROR_STRAINERBLOCK", "Strainer blocked"),
    DeviceError(119, "ERROR_FANERROR", "Fan error"),
    DeviceError(120, "ERROR_WATERBOX_ERROR", "Water box error"),
    DeviceError(121, "ERROR_PLATE_JAMMED", "Plate jammed"),
    DeviceError(125, "ERROR_HARDWIPE_TANK_MACHINERY_ERROR", "Hard wipe tank machinery error"),
    DeviceError(126, "ERROR_NO_HARDWIPE_TANK", "No hard wipe tank"),
    DeviceError(127, "ERROR_NO_HARDWIPE_BRUSH", "No hard wipe brush"),
    DeviceError(128, "ERROR_SET_HARDWIPE_BRUSH", "Hard wipe brush not set"),
    DeviceError(129, "ERROR_BIND_HARDWIPE_BRUSH", "Hard wipe brush not bound"),
    DeviceError(201, "ERROR_AIRFILTERUNISTALL", "Air filter not installed"),
    DeviceError(202, "ERROR_ULTRASONICCOMPONENTABNORMAL", "Ultrasonic component abnormal"),
    DeviceError(203, "ERROR_SMALLWHEELERROR", "Small wheel error"),
    DeviceError(204, "ERROR_WHEEL_HANG", "Wheel hang"),
    DeviceError(205, "ERROR_ION_STERILIZE_EXHAUSTED", "Ion sterilize exhausted"),
    DeviceError(206, "ERROR_ION_STERILIZE_ABNORMAL", "Ion sterilize abnormal"),
    DeviceError(207, "ERROR_ION_STERILIZE_FAULT", "Ion sterilize fault"),
    DeviceError(209, "ERROR_DTOF_ABNORMAL", "dToF sensor abnormal"),
    DeviceError(301, "ERROR_MCD_NO_CLEANWATER", "Mop station: no clean water"),
    DeviceError(302, "ERROR_MCD_FULL_DIRTYWATER", "Mop station: dirty water full"),
    DeviceError(303, "ERROR_MCD_NO_CLEANWATER_TANK", "Mop station: no clean water tank"),
    DeviceError(304, "ERROR_MCD_NO_DIRTYWATER_TANK", "Mop station: no dirty water tank"),
    DeviceError(305, "ERROR_MCD_CLEANTANK_ERROR", "Mop station: clean tank error"),
    DeviceError(306, "ERROR_MCD_NO_CLEANTANK_WEB", "Mop station: clean tank not connected"),
    DeviceError(307, "ERROR_MCD_MACHINERY_ERROR", "Mop station: machinery error"),
    DeviceError(308, "ERROR_MCD_CONNECTION_ERROR", "Mop station: connection error"),
    DeviceError(309, "ERROR_TANK_TOOHOT_ERROR", "Water tank too hot"),
    DeviceError(310, "ERROR_AUTO_EMPTY_OPEN", "Auto empty station: lid open"),
    DeviceError(311, "ERROR_AUTO_EMPTY_UNINSTALL", "Auto empty station: not installed"),
    DeviceError(312, "ERROR_AUTO_EMPTY_FULL", "Auto empty station: dust bag full"),
    DeviceError(313, "ERROR_AUTO_EMPTY_UNKNOWN", "Auto empty station: unknown error"),
    DeviceError(314, "ERROR_BASE_STATION_WATER_UNINSTALL", "Base station: water filter not installed"),
    DeviceError(315, "ERROR_BASE_STATION_SILVER_UNINSTALL", "Base station: silver module not installed"),
    DeviceError(316, "ERROR_BASE_STATION_FULL_UNINSTALL", "Base station: dust bag not installed"),
    DeviceError(317, "ERROR_BASE_STATION_UD_WATER_UNINSTALL", "Base station: undiluted water module not installed"),
    DeviceError(318, "ERROR_BASE_STATION_UD_WATER_FULL", "Base station: undiluted water full"),
    DeviceError(319, "ERROR_BASE_STATION_CLEAN_WATER_EMPTY", "Base station: clean water empty"),
    DeviceError(601, "ERROR_ClosedAIVISideAbnormal", "Closed AI vision: side abnormal"),
    DeviceError(602, "ERROR_ClosedAIVIRollAbnormal", "Closed AI vision: roller abnormal"),
)

# The errors by their number, for a quick lookup.
DEVICE_ERRORS_BY_CODE: dict[int, DeviceError] = {error.code: error for error in DEVICE_ERRORS}


def describe(code: int | None) -> str:
    """Return what an error code means.

    A code the robot does not know is returned as it is, so nothing is lost.
    """
    if code is None:
        return ""
    error = DEVICE_ERRORS_BY_CODE.get(code)
    if error is None:
        return f"Unknown error ({code})"
    return f"{error.description} ({code})"
