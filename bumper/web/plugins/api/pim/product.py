"""Pim product plugin module."""

from collections.abc import Iterable
import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import (
    get_bot_image_path,
    get_config_groups_response,
    get_config_net_all_response,
    get_product_config_batch,
    get_product_entry_group,
    get_product_info_by_mids,
    get_product_iot_map,
)
from bumper.web.utils.response_helper import response_success_v3, response_success_v4

_LOGGER = logging.getLogger(__name__)


class ProductPlugin(WebserverPlugin):
    """Product plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/product/getProductIotMap", _handle_get_product_iot_map),
            web.route("*", "/product/getConfignetAll", _handle_get_config_net_all),
            web.route("*", "/product/getConfigGroups", _handle_get_config_groups),
            web.route("POST", "/product/software/config/batch", _handle_config_batch),
            web.route("POST", "/product/getShareInfo", _handle_get_share_info),
            web.route("GET", "/product/image", _get_bot_image),
            web.route("GET", "/product/entry/group", _get_entry_group),
            web.route("GET", "/product/info", _handle_product_info),
        ]


async def _handle_get_product_iot_map(_: Request) -> Response:
    """Get product iot map."""
    return response_success_v4(get_product_iot_map())


async def _handle_get_config_net_all(_: Request) -> Response:
    """Get config net all."""
    return response_success_v3(
        code=0,
        msg_key="msg",
        msg="success",
        result_key="configFAQ",
        result={
            "wifiFAQUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/faqproblem.html?lang=en&defaultLang=en",
            "notFoundAPUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/findDbWifi.html?lang=en&defaultLang=en",
            "configFailedUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/configfail.html?lang=en&defaultLang=en",
        },
        data_key="data",
        data=get_config_net_all_response(),
    )


async def _handle_get_config_groups(_: Request) -> Response:
    """Get config groups."""
    return response_success_v3(
        code=0,
        msg_key="msg",
        msg="success",
        result_key="configFAQ",
        result={
            "wifiFAQUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/faqproblem.html?lang=en&defaultLang=en",
            "notFoundAPUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/findDbWifi.html?lang=en&defaultLang=en",
            "configFailedUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/configfail.html?lang=en&defaultLang=en",
        },
        data_key="data",
        data=get_config_groups_response(),
    )


async def _handle_config_batch(request: Request) -> Response:
    """Handle product config batch."""
    try:
        product_config_batch: list[dict[str, Any]] = get_product_config_batch()

        # Build a pid -> config dict for fast lookup
        pid_to_config = {item.get("pid", ""): item for item in product_config_batch}

        json_body = json.loads(await request.text())
        data = []
        for pid in json_body.get("pids", []):
            if config := pid_to_config.get(pid):
                data.append(config)
            else:
                # not found in product_config_batch
                data.append({"cfg": {}, "pid": pid})

        return response_success_v3(data=data, code=200)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_get_share_info(request: Request) -> Response:
    """Get share info."""
    try:
        json_body = json.loads(await request.text())
        scene = json_body.get("scene")
        _LOGGER.debug(f"Share info :: {scene}")
        return response_success_v4([])
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _get_bot_image(_: Request) -> FileResponse:
    """Get generic image of bot."""
    return FileResponse(get_bot_image_path())


async def _get_entry_group(_: Request) -> Response:
    """Get entry group."""
    return response_success_v3(data=get_product_entry_group())


async def _handle_product_info(request: Request) -> Response:
    """Get product info for the requested mids.

    Served locally so the request is not proxied upstream (the real cloud rejects
    bumper-minted credentials). Synthesized generically per-mid from the config
    groups data, so any known device works, not just a hardcoded subset.
    """
    try:
        mids_param = request.query.get("mids", "")
        mids = [mid for mid in (m.strip() for m in mids_param.split(",")) if mid]
        return response_success_v4(get_product_info_by_mids(mids))
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError
