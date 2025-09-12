"""CA certificates plugin module."""

import asyncio
from collections.abc import Iterable
import hashlib
import logging
from pathlib import Path
import tarfile
import tempfile

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin

_LOGGER = logging.getLogger(__name__)

_CA_CERTIFICATES = "ca-certificates"
_CA_FILE = f"{_CA_CERTIFICATES}.crt"
_MD5_FILE = "MD5SUMS"

_TEMP_DIR = Path(tempfile.mkdtemp(prefix="bumper_ca_certificates_"))
_CA_ARCHIVE_FILENAME = f"{_CA_CERTIFICATES}.tar.gz"
_CA_ARCHIVE_FILE = _TEMP_DIR / _CA_ARCHIVE_FILENAME

_LOCK = asyncio.Lock()


class CaCertificatesPlugin(WebserverPlugin):
    """CA certificates plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "GET",
                f"/{_CA_ARCHIVE_FILENAME}",
                _handler_ca_certificates,
            ),
        ]


# bumper_isc.ca_cert
async def _handler_ca_certificates(_: Request) -> FileResponse:
    """Return the ca-certificates.tar.gz archive."""
    async with _LOCK:
        if not _CA_ARCHIVE_FILE.exists():
            await asyncio.get_event_loop().run_in_executor(None, _create_ca_certificates_archive)

    try:
        return FileResponse(_CA_ARCHIVE_FILE)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


def _create_ca_certificates_archive() -> None:
    _LOGGER.debug("Creating CA certificates archive...")

    with bumper_isc.ca_cert.open("rb") as f:
        cert_data = f.read()

    cert_file_path = _TEMP_DIR / _CA_FILE
    with cert_file_path.open("wb") as f:
        f.write(cert_data)

    md5_sum = hashlib.md5(cert_data).hexdigest()  # noqa: S324
    _LOGGER.debug(f"MD5 sum: {md5_sum}")
    md5_file_path = _TEMP_DIR / _MD5_FILE
    with md5_file_path.open("w") as f:
        f.write(md5_sum)

    with tarfile.open(_CA_ARCHIVE_FILE, "w:gz") as tar:
        tar.add(cert_file_path, arcname=_CA_FILE)
        tar.add(md5_file_path, arcname=_MD5_FILE)

    _LOGGER.debug(f"Successfully created {_CA_ARCHIVE_FILE}")
