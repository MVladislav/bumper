"""Voice plugin module."""

from collections.abc import Iterable
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_voices
from bumper.web.utils.response_helper import response_success_v3

_LOGGER = logging.getLogger(__name__)


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
    """Get the voice of a language."""
    try:
        body = await _request_body(request)
        voice_lang = str(body.get("voiceLang", "EN")).lower()
        voice = _voice(voice_lang)
        if voice is None:
            _LOGGER.warning(f"No voice data for language :: {voice_lang}")
            return response_success_v3(data_key="voices", data=[])
        return response_success_v3(data_key="voices", data=[voice])
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise web.HTTPInternalServerError


async def _handle_get_lanuages(_: Request) -> Response:
    """Get languages."""
    return response_success_v3(data_key="voices", data=_get_voice_list())


async def _handle_download(request: Request) -> Response:
    """Download a voice file.

    The robot downloads the file from here to install a voice. The files are
    not part of the distribution, so the answer is 404 until one is put in the
    voice directory under the id of the language.
    """
    voice_id = request.match_info.get("id", "")
    voice_file = Path(bumper_isc.voice_dir) / voice_id
    if not voice_id or not voice_file.is_file():
        _LOGGER.warning(f"No voice file for id={voice_id} :: looked in '{bumper_isc.voice_dir}'")
        return web.Response(status=404, body=b"", content_type="text/plain", charset="utf-8")
    return web.FileResponse(voice_file)  # type: ignore[return-value]


def _voice(voice_lang: str) -> dict[str, Any] | None:
    """Return the voice data of a language, with the URLs pointed at Bumper."""
    voice = get_voices().get(voice_lang)
    if not isinstance(voice, dict):
        return None
    return {
        **voice,
        "voiceLang": voice_lang,
        "languageName": _language_name(voice_lang),
        # The robot downloads the file itself, so it needs an absolute URL.
        "iconUrl": _absolute(voice.get("iconUrl", "")),
        "sampleVoiceUrl": _absolute(voice.get("sampleVoiceUrl", "")),
        "voiceUrl": _absolute(voice.get("voiceUrl", "")),
        "status": "valid",
        "desc": "",
        "tag": "",
        "support": ["yiko"],
        "advertisementPhotoUrl": "",
        "isDefault": True,
        "needActive": False,
    }


def _absolute(path: str) -> str:
    """Return the path as a URL the robot can download."""
    if not path:
        return ""
    if path.startswith("http"):
        return path
    return f"https://api-app.{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}{path}"


def _language_name(voice_lang: str) -> str:
    """Return the name of a language."""
    for voice in _get_voice_list():
        if voice["voiceLang"] == voice_lang:
            return str(voice["languageName"])
    return voice_lang


def _get_voice_list() -> list[dict[str, str | list[str]]]:
    """Return the languages the app offers a voice for."""
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


async def _request_body(request: Request) -> dict[str, Any]:
    """Return the JSON body of a request, or an empty dict."""
    try:
        body = json.loads(await request.text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return body if isinstance(body, dict) else {}
