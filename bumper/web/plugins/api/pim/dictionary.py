"""Pim dictionary plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v3


class DictionaryPlugin(WebserverPlugin):
    """Dictionary plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "*",
                "/dictionary/getErrDetail",
                _handle_get_err_detail,
            ),
        ]


async def _handle_get_err_detail(_: Request) -> Response:
    """Get error details."""
    return response_success_v3(
        code=0,
        msg_key="msg",
        msg="success",
        data_key="data",
        data=[
            {
                "code": "10000",
                "msg": (
                    "Error code: 10000, 10020, 10021 - The mobile device is not connected to the network\r\n"
                    "Make sure both your mobile device and home Wi-Fi can access the Internet."
                ),
            },
            {
                "code": "10002",
                "msg": (
                    "Error code: 2, 10002, 10024 -Programe error\r\n"
                    "Please restart the App, reboot Robot (turn it off, and then turn it back on), and try again."
                ),
            },
            {
                "code": "10006",
                "msg": (
                    "Error code: 10006, 10011 - Network connection timed out\r\n"
                    "Make sure both your mobile device and home Wi-Fi can access the Internet."
                ),
            },
            {
                "code": "10010",
                "msg": (
                    "Unable to connect the robot to the network -【10010】、【10018】、【10025】: <div><ul><li>Make sure "
                    "the connected home Wi-Fi network is a 2.4GHz or 2.4/5GHz mixed network.</li><li>Make sure that "
                    "the robot is in an area with good Wi-Fi coverage. We recommend using the robot within 3 meters "
                    "of the scope of your home Wi-Fi.</li><li>Please confirm that the robot is turned on and in the "
                    "network configuration standby mode.</li><li>Make sure that the home Wi-Fi password you've entered "
                    "is correct.</li><li>Make sure that the home Wi-Fi connected to the mobile device is the same as "
                    "that connected to the robot.</li></ul></div>"
                ),
            },
            {
                "code": "10011",
                "msg": (
                    "Error code: 10006, 10011 - Network connection timed out\r\n"
                    "Make sure both your mobile device and home Wi-Fi can access the Internet."
                ),
            },
            {
                "code": "10016",
                "msg": (
                    "Error code: 10016, 10017 - Device configuration timed out\r\nMake sure the phone's mobile data, "
                    "such as its 4G network, is turned off.\r\nMake sure your phone is connected to the Robot Wi-Fi.\r\n"
                    'If you cannot see the "ECOVACS_xxxx" Wi-Fi, reboot Robot (press and hold the Reset button until a '
                    "startup sound is played) and the router; then force quit the app and try again"
                ),
            },
            {
                "code": "10017",
                "msg": (
                    "Error code: 10016, 10017 - Device configuration timed out\r\nMake sure the phone's mobile data, "
                    "such as its 4G network, is turned off.\r\nMake sure your phone is connected to the Robot Wi-Fi.\r\n"
                    'If you cannot see the "ECOVACS_xxxx" Wi-Fi, reboot Robot (press and hold the Reset button until a '
                    "startup sound is played) and the router; then force quit the app and try again"
                ),
            },
            {
                "code": "10018",
                "msg": (
                    "Unable to connect the robot to the network -【10010】、【10018】、【10025】: <div><ul><li>Make sure "
                    "the connected home Wi-Fi network is a 2.4GHz or 2.4/5GHz mixed network.</li><li>Make sure that "
                    "the robot is in an area with good Wi-Fi coverage. We recommend using the robot within 3 meters "
                    "of the scope of your home Wi-Fi.</li><li>Please confirm that the robot is turned on and in the "
                    "network configuration standby mode.</li><li>Make sure that the home Wi-Fi password you've entered "
                    "is correct.</li><li>Make sure that the home Wi-Fi connected to the mobile device is the same as "
                    "that connected to the robot.</li></ul></div>"
                ),
            },
            {
                "code": "10020",
                "msg": (
                    "Error code: 10000, 10020, 10021 - The mobile device is not connected to the network\r\n"
                    "Make sure both your mobile device and home Wi-Fi can access the Internet."
                ),
            },
            {
                "code": "10021",
                "msg": (
                    "Error code: 10000, 10020, 10021 - The mobile device is not connected to the network\r\n"
                    "Make sure both your mobile device and home Wi-Fi can access the Internet."
                ),
            },
            {
                "code": "10024",
                "msg": (
                    "Error code: 2, 10002, 10024 -Programe error\r\n"
                    "Please restart the App, reboot Robot (turn it off, and then turn it back on), and try again."
                ),
            },
            {
                "code": "10025",
                "msg": (
                    "Unable to connect the robot to the network -【10010】、【10018】、【10025】: <div><ul><li>"
                    "Make sure the connected home Wi-Fi network is a 2.4GHz or 2.4/5GHz mixed network.</li><li>"
                    "Make sure that the robot is in an area with good Wi-Fi coverage. We recommend using the robot "
                    "within 3 meters of the scope of your home Wi-Fi.</li><li>Please confirm that the robot is turned "
                    "on and in the network configuration standby mode.</li><li>Make sure that the home Wi-Fi password "
                    "you've entered is correct.</li><li>Make sure that the home Wi-Fi connected to the mobile device "
                    "is the same as that connected to the robot.</li></ul></div>"
                ),
            },
            {
                "code": "10503",
                "msg": (
                    "Error code: 10503 - Timed out while receiving network setup info\r\n"
                    'Please keep your phone connected to the "ECOVACS_xxxx" Wi-Fi before the progress bar exceeds 50%.'
                ),
            },
            {
                "code": "2",
                "msg": (
                    "Error code: 2, 10002, 10024 -Programe error\r\n"
                    "Please restart the App, reboot Robot (turn it off, and then turn it back on), and try again."
                ),
            },
            {
                "code": "3",
                "msg": "Error code: 3 - Login timed out\r\nPlease log in to your account and try again.",
            },
        ],
    )
