"""Voice plugin module."""

# import logging
from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v3


class VoicePlugin(WebserverPlugin):
    """Voice plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/voice/get", _handle_get),
            web.route("*", "/voice/getLanuages", _handle_get_lanuages),
            web.route("*", "/v2/voice/getLanuages", _handle_get_lanuages),
            web.route("*", "/voice/download/{id}", _handle_download),
        ]


async def _handle_get(request: Request) -> Response:
    """Get voice."""
    voice_lang = request.query.get("voiceLang", "EN").lower()
    language_name = next((v.get("languageName") for v in _get_voice_list() if v.get("voiceLang") == voice_lang), "English")
    return response_success_v3(
        data_key="voices",
        data=[
            {
                "advertisementPhotoUrl": "",
                "desc": "",
                "downloadTimes": 65,
                "iconUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61a8912cd302838d8898df9b",
                "id": "default",
                "isDefault": True,
                "languageName": language_name,
                "name": language_name,
                "needActive": False,
                "sampleVoiceUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/file/get/61a8913a72e305f1cac11617",
                "sort": 401,
                "status": "valid",
                "support": ["yiko"],
                "tag": "",
                "voice": "65279265545c5fc089782ab8",  # pragma: allowlist secret
                "voiceLang": voice_lang,
                "voiceMd5": "27a816e229a0e0471703a244a7763f09",  # pragma: allowlist secret
                "voiceSize": 3823807,
                "voiceUrl": f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/voice/download/61a89146d30283475c98df9d",
            },
        ],
    )


async def _handle_get_lanuages(_: Request) -> Response:
    """Get languages."""
    return response_success_v3(data_key="voices", data=_get_voice_list())


def _get_voice_list() -> list[dict[str, str | list[str]]]:
    return [
        {"voiceLang": "en", "languageName": "English", "support": ["yiko"]},
        {"voiceLang": "en-au", "languageName": "English(Australian)", "support": ["yiko"]},
        {"voiceLang": "en-ca", "languageName": "English(Canadian)", "support": ["yiko"]},
        {"voiceLang": "en-gb", "languageName": "English(United Kingdom)", "support": ["yiko"]},
        {"voiceLang": "en-in", "languageName": "English(Indian)", "support": ["yiko"]},
        {"voiceLang": "en-us", "languageName": "English(American)", "support": ["yiko"]},
        {"voiceLang": "ko", "languageName": "한국어", "support": ["yiko"]},
        {"voiceLang": "ja", "languageName": "日本語", "support": ["yiko"]},
        {"voiceLang": "fr", "languageName": "Le français", "support": ["yiko"]},
        {"voiceLang": "tw", "languageName": "國語", "support": ["yiko"]},
        {"voiceLang": "de", "languageName": "Deutsch", "support": ["yiko"]},
        {"voiceLang": "it", "languageName": "Italiano", "support": ["yiko"]},
        {"voiceLang": "id", "languageName": "Indonesia", "support": ["yiko"]},
    ]


async def _handle_download(_: Request) -> Response:
    """Download."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_download")
    return response_success_v3(data_key="voices", data=None)
