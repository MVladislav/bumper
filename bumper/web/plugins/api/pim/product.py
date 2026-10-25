"""Pim product plugin module."""

import logging
from typing import Any

from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.web.context import read_body
from bumper.web.envelope import LEGACY, LEGACY_BARE, LEGACY_MSG, LEGACY_NO_RET, bind
from bumper.web.hosts import pim_host
from bumper.web.static_api import (
    get_bot_image_path,
    get_config_groups_response,
    get_config_net_all_response,
    get_product_config_batch,
    get_product_entry_group,
    get_product_iot_map,
)

from . import PREFIX

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/product/getProductIotMap")
@bind(LEGACY_BARE)
async def _handle_get_product_iot_map(_: Request) -> Any:
    """Get product iot map."""
    return get_product_iot_map()


@routes.view(f"{PREFIX}/product/getConfignetAll")
@bind(
    LEGACY_MSG.with_code(0)
    .with_data_key("data")
    .with_side_car(
        "configFAQ",
        {
            "wifiFAQUrl": f"https://{pim_host()}/api/pim/faqproblem.html?lang=en&defaultLang=en",
            "notFoundAPUrl": f"https://{pim_host()}/api/pim/findDbWifi.html?lang=en&defaultLang=en",
            "configFailedUrl": f"https://{pim_host()}/api/pim/configfail.html?lang=en&defaultLang=en",
        },
    ),
)
async def _handle_get_config_net_all(_: Request) -> Any:
    """Get config net all."""
    return get_config_net_all_response()


@routes.view(f"{PREFIX}/product/getConfigGroups")
@bind(
    LEGACY_MSG.with_code(0)
    .with_data_key("data")
    .with_side_car(
        "configFAQ",
        {
            "wifiFAQUrl": f"https://{pim_host()}/api/pim/faqproblem.html?lang=en&defaultLang=en",
            "notFoundAPUrl": f"https://{pim_host()}/api/pim/findDbWifi.html?lang=en&defaultLang=en",
            "configFailedUrl": f"https://{pim_host()}/api/pim/configfail.html?lang=en&defaultLang=en",
        },
    ),
)
async def _handle_get_config_groups(_: Request) -> Any:
    """Get config groups."""
    return get_config_groups_response()


@routes.post(f"{PREFIX}/product/software/config/batch")
@bind(LEGACY.with_code(200))
async def _handle_config_batch(request: Request) -> Any:
    """Handle product config batch."""
    product_config_batch: list[dict[str, Any]] = get_product_config_batch()

    # Build a pid -> config dict for fast lookup
    pid_to_config = {item.get("pid", ""): item for item in product_config_batch}

    json_body = await read_body(request)
    data = []
    for pid in json_body.get("pids", []):
        if config := pid_to_config.get(pid):
            data.append(config)
        else:
            # not found in product_config_batch
            data.append({"cfg": {}, "pid": pid})

    return data


@routes.post(f"{PREFIX}/product/getShareInfo")
async def _handle_get_share_info(request: Request) -> Response:
    """Get share info."""
    json_body = await read_body(request)
    scene = json_body.get("scene")
    _LOGGER.debug(f"Share info :: {scene}")
    return web.json_response(
        {
            "code": 0,
            "shareInfo": {
                "keyword": "",
                "url": "",
                "shareText": "",
                "shareDesc": "",
                "shareUrl": "",
            },
        },
    )


@routes.get(f"{PREFIX}/product/image")
async def _get_bot_image(_: Request) -> FileResponse:
    """Get generic image of bot."""
    return FileResponse(get_bot_image_path())


@routes.get(f"{PREFIX}/product/entry/group")
@bind(LEGACY_NO_RET)
async def _get_entry_group(_: Request) -> Any:
    """Get entry group."""
    return get_product_entry_group()


@routes.view(f"{PREFIX}/product/setting")
@bind(LEGACY_NO_RET)
async def _handle_product_setting(request: Request) -> Any:
    """Get product settings."""
    _LOGGER.debug(
        f"Product setting requested :: mids={request.query.get('mids', '')} :: modules={request.query.get('modules', '')}",
    )
    return {}
