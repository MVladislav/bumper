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
    recommendation: str = (
        "Check the Ecovacs app for model-specific steps. If the issue persists, record the error code and contact support."
    )


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
    DeviceError(401, "ERROR_TILT", "Tilt"),
    DeviceError(402, "ERROR_OVERHANG", "Overhang"),
    DeviceError(403, "ERROR_SENSOR", "Sensor"),
    DeviceError(404, "ERROR_BATTERY", "Battery"),
    DeviceError(405, "ERROR_LEFT_DRIVING_WHEEL", "Left driving wheel"),
    DeviceError(406, "ERROR_ROTATION_CUTTER_HEAD", "Rotation cutter head"),
    DeviceError(407, "ERROR_BUMP_PLATE", "Bump plate"),
    DeviceError(408, "ERROR_TO_ERASE", "To erase"),
    DeviceError(409, "ERROR_CLEAN_LENS", "Clean lens"),
    DeviceError(410, "ERROR_GET_LOST", "Get lost"),
    DeviceError(411, "ERROR_STATION_LOCATION", "Station location"),
    DeviceError(412, "ERROR_BEACON_LOCATION", "Beacon location"),
    DeviceError(414, "ERROR_RGBD_DIRTY", "RGBD dirty"),
    DeviceError(415, "ERROR_PANORAMIC_CAMEAR_DIRTY", "Panoramic camera dirty"),
    DeviceError(416, "ERROR_BATTERY_HIGH_TEMPERATURE", "Battery high temperature"),
    DeviceError(417, "ERROR_BATTERY_LOW_TEMPERATURE", "Battery low temperature"),
    DeviceError(418, "ERROR_IN_FORBIDDEN_AREA", "In forbidden area"),
    DeviceError(420, "ERROR_OUT_OF_MAP_RANGE", "Out of map range"),
    DeviceError(421, "ERROR_BEACON_SINGAL", "Beacon signal"),
    DeviceError(422, "ERROR_GPS_SIGNAL_WEAK_BACK", "GPS signal weak back"),
    DeviceError(423, "ERROR_GPS_SIGNAL_WEAK_WAIT", "GPS signal weak wait"),
    DeviceError(424, "ERROR_RIGHT_DRIVING_WHEEL", "Right driving wheel"),
    DeviceError(430, "ERROR_SENSOR430", "Sensor 430"),
    DeviceError(431, "ERROR_SENSOR431", "Sensor 431"),
    DeviceError(432, "ERROR_SENSOR432", "Sensor 432"),
    DeviceError(433, "ERROR_SENSOR433", "Sensor 433"),
    DeviceError(434, "ERROR_SENSOR434", "Sensor 434"),
    DeviceError(435, "ERROR_SENSOR435", "Sensor 435"),
    DeviceError(520, "ERROR_TRAPPED", "Trapped"),
    DeviceError(601, "ERROR_ClosedAIVISideAbnormal", "Closed AI vision: side abnormal"),
    DeviceError(602, "ERROR_ClosedAIVIRollAbnormal", "Closed AI vision: roller abnormal"),
)

# The errors by their number, for a quick lookup.
DEVICE_ERRORS_BY_CODE: dict[int, DeviceError] = {error.code: error for error in DEVICE_ERRORS}

_DEVICE_ERROR_RECOMMENDATIONS: dict[int, str] = {
    101: "Return the robot to its charging station and allow it to charge before resuming.",
    103: "Check the wheels for wrapped hair or debris. Clear the obstruction before restarting the robot.",
    104: "Wipe the downward-facing sensors with a soft, dry cloth and move the robot to a well-lit, clear floor.",
    105: "Move the robot to a clear, level area and remove anything trapping it before resuming.",
    106: "Clean the side brush and replace it if the bristles are worn.",
    108: "Check the side brush for wrapped debris and confirm it turns freely.",
    109: "Remove hair and debris from the roller and check that it turns freely.",
    110: "Reinstall the dust box and confirm it is seated correctly.",
    111: "Check that the bumper moves freely and clear any debris around it.",
    112: "Clear objects around the laser sensor and check that its cover can rotate freely.",
    113: "Clean the main brush and replace it if it is worn.",
    114: "Empty and reinstall the dust box.",
    301: "Refill and reinstall the clean-water tank.",
    302: "Empty and reinstall the dirty-water tank.",
    303: "Install the clean-water tank and confirm it is seated correctly.",
    304: "Install the dirty-water tank and confirm it is seated correctly.",
    310: "Close the auto-empty station lid and retry.",
    312: "Replace the dust bag and reset the station indicator if the model requires it.",
    319: "Refill the station's clean-water tank.",
    401: "Place the mower on a level surface and check that it is not tilted or lifted.",
    402: "Move the mower away from an edge or overhang and place it on supported ground.",
    409: "Clean the mower lens with a soft, dry cloth.",
    418: "Move the mower out of the forbidden area or update the boundary in the app.",
    420: "Return the mower inside the mapped work area and check the map boundaries.",
    520: "Free the mower from the obstruction and place it on stable, open ground before resuming.",
}


def describe(code: int | None, *, include_code: bool = True) -> str:
    """Return what an error code means.

    A code the robot does not know is returned as it is, so nothing is lost.
    """
    if code is None:
        return ""
    error = DEVICE_ERRORS_BY_CODE.get(code)
    if error is None:
        return f"Unknown error ({code})" if include_code else "Unknown error"
    return f"{error.description} ({code})" if include_code else error.description


def recommendation(code: int | None) -> str:
    """Return a cautious next step for a known error code."""
    if code is None:
        return "Check the robot and the Ecovacs app for the current status."
    return _DEVICE_ERROR_RECOMMENDATIONS.get(
        code,
        (
            "Check the robot and the Ecovacs app for model-specific recovery steps. "
            "If it persists, record this code and contact support."
        ),
    )
