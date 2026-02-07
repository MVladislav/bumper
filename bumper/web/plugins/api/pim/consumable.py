"""Pim consumable plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v3

_LOGGER = logging.getLogger(__name__)


class ConsumablePlugin(WebserverPlugin):
    """Consumable plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/consumable/getPurchaseUrl", _handle_get_purchase_url),
        ]


async def _handle_get_purchase_url(_: Request) -> Response:
    """Get purchase url."""
    desc_side_brush = (
        "Dual Side Brushes can collect dust and send it to the Main Brush, so as to better clean the corners."
        " In the process of cleaning, the Side Brush may get entangled with hair. Please remove the hair with"
        " the multi-function cleaning tool promptly. To get the best cleaning experience, it is recommended to"
        " change the Side Brush every 150 hours of work or less.  If you wish to purchase our special"
        " multi-function cleaning tool, visit our store online or in the ECOVACS HOME App."
    )
    desc_main_brush = (
        "Main Brush is the main cleaning component of DEEBOT, which can pick up debris on the floor and send it to"
        " the Dust Bin. In the process of cleaning, the Main Brush may be tangled with hair. Please remove the hair"
        " with the multi-function cleaning tool promptly. To get the best cleaning experience, it is recommended to"
        " change the Main Brush every 300 hours of cleaning or less. If you wish to purchase our special multi-function"
        " cleaning tool, visit our store online or in the ECOVACS HOME App."
    )
    desc_filter = (
        "When DEEBOT is cleaning, the filter can effectively prevent the dust in the Dust Bin from escaping."
        " With an increase in cleaning duration, dust may gradually block the filter and affect cleaning efficiency."
        " Rinse the filter with water and dry it thoroughly every two weeks. It is recommended to change the filter"
        " every 120 hours of cleaning or less."
    )
    desc_dust_bag = (
        "The Dust Bag is an accessory for the Station; it is recommended to use it with a station that supports"
        " Auto-Empty feature. When cleaning is complete, DEEBOT will return to the Station and automatically empty"
        " the Dust Bin, saving you time and effort. To get the best cleaning experience, it is recommended to regularly"
        " replace the Dust Bag and clean the Dust Bag Cabin once a month."
    )
    desc_disposable_cleaning_cloth = (
        "DEEBOT is compatible with a Disposable Cleaning Cloth for mopping, which is easy to apply and dispose of,"
        " does not need to be washed, and prevents the breeding of bacteria from prolonged storage of a damp cloth."
        " To get the best cleaning experience, it is recommended to dispose of the Disposable Cleaning Cloth every"
        " time after mopping."
    )
    desc_other_components = (
        "1. DEEBOT Maintenance: After DEEBOT has been working for a while, components will be contaminated with dust,"
        " hair and other debris, which will reduce cleaning efficiency. It is recommended to wipe up the dust with a dry"
        " cloth and remove the hair with the multi-function cleaning tool every 30 hours of cleaning or less."
        " For more information, please refer to the instruction manual.  If you wish to purchase our special multi-function"
        " cleaning tool, visit our store online or in the ECOVACS HOME App."
    )
    desc_air_freshener_capsule = (
        "DEEBOT can diffuse fragrance via Air Freshener while cleaning. To get the best air freshening experience,"
        " it is recommended to change the Air Freshening Capsule every 60 hours or less."
    )

    return response_success_v3(
        msg_key="msg",
        data=[
            {
                "id": "62df48fe55e82d6b346214d9",  # pragma: allowlist secret
                "name": "Side Brush",
                "icon": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61a5f036ed50344bd5b52819",
                "url": "",
                "paramType": "URL",
                "type": "sideBrush",
                "sort": 0,
                "desc": {
                    "images": [
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65a53a95a16082ef62b75",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65a5370c881b5d965ebd6",
                    ],
                    "content": desc_side_brush,
                },
                "hasLifeSpan": 0,
            },
            {
                "id": "62df495e176a4d3d8780acdc",  # pragma: allowlist secret
                "name": "Main Brush",
                "icon": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61a5f0a45afd254c7a5c6959",
                "url": "",
                "paramType": "URL",
                "type": "brush",
                "sort": 1,
                "desc": {
                    "images": [
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65a6470c881359c65ebd7",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65a649d1b811cd1574677",
                    ],
                    "content": desc_main_brush,
                },
                "hasLifeSpan": 0,
            },
            {
                "id": "6284c3c0dd78021dc557ffbe",  # pragma: allowlist secret
                "name": "Filter",
                "icon": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61a5f0e472e3052928c1160a",
                "url": "",
                "paramType": "URL",
                "type": "heap",
                "sort": 2,
                "desc": {
                    "images": [
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65a77843b5ac787b74e36",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65a77fd39e41ee3132ded",
                    ],
                    "content": desc_filter,
                },
                "hasLifeSpan": 0,
            },
            {
                "id": "62df49bb55e82d2a2c6214de",  # pragma: allowlist secret
                "name": "Dust Bag",
                "icon": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61a5f1fded5034391bb5281a",
                "url": "",
                "paramType": "URL",
                "type": "dustBag",
                "sort": 3,
                "desc": {
                    "images": [
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65a889ee4d3820c02cd71",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65a8870c88178a665ebd8",
                    ],
                    "content": desc_dust_bag,
                },
                "hasLifeSpan": 0,
            },
            {
                "id": "6284c3c6dd7802847257ffc3",  # pragma: allowlist secret
                "name": "Disposable Cleaning Cloth",
                "icon": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d6592cfe802336b9d12e7d",
                "url": "",
                "paramType": "URL",
                "type": "oneTimeCloth",
                "sort": 5,
                "desc": {
                    "images": [
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d659c89ee4d39fc802cd6d",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d659c8843b5a8597b74e35",
                    ],
                    "content": desc_disposable_cleaning_cloth,
                },
                "hasLifeSpan": 0,
            },
            {
                "id": "6284c3c9dd78023a6057ffc5",  # pragma: allowlist secret
                "name": "Other Components",
                "icon": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61a5f38172e305764bc1160c",
                "url": "",
                "paramType": "URL",
                "type": "unitCare",
                "sort": 6,
                "desc": {
                    "images": [
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65aa4fd39e4647a132dee",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65aa470c88112d965ebd9",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65aa4fe80236a34d12e7f",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65aa4fd39e448e0132def",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65aa4843b5a5049b74e37",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65aa470c881c28865ebda",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d65aa470c8814e1c65ebdb",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/629471d79dbd618f3fbb501e",
                    ],
                    "content": desc_other_components,
                },
                "hasLifeSpan": 0,
            },
            {
                "id": "6284c3ccdd78024ea157ffc7",  # pragma: allowlist secret
                "name": "Air Freshener Capsule",
                "icon": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d659e6fd39e48ab8132dec",
                "url": "",
                "paramType": "URL",
                "type": "dModule",
                "sort": 7,
                "desc": {
                    "images": [
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d659fa9ee4d3154402cd6e",
                        f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61d659fa9ee4d345dd02cd6f",
                    ],
                    "content": desc_air_freshener_capsule,
                },
                "hasLifeSpan": 0,
            },
        ],
    )
