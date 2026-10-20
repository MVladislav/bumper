"""Manage the files the robot uploads to the data-collect endpoint.

The robot posts two kinds of payload there: a picture of the camera patrol and
the cleaned map of a finished job. Both are listed to the app as photos, so
they are kept in one table and told apart by the `kind` field.
"""

import base64
from collections.abc import Callable
import json
import logging
from typing import Any, cast

from tinydb.table import Document

from bumper.utils.utils import to_int, to_milliseconds
from bumper.web.utils.models import CleanLog

from .base import BaseRepo
from .db import TABLE_PHOTOS, query_instance

_LOGGER = logging.getLogger(__name__)

KIND_PICTURE = "pic"
KIND_MAP = "map"


class PhotoRepo(BaseRepo):
    """DAO for photos."""

    def __init__(self) -> None:
        super().__init__(TABLE_PHOTOS)

    def add(self, photo: dict[str, Any]) -> None:
        """Store a photo record."""
        self.table.insert(photo)

    def list_all(self) -> list[dict[str, Any]]:
        """Return all photo records."""
        return [doc for doc in self.table.all() if isinstance(doc, dict | Document)]

    def list_by_did(
        self,
        did: str | None = None,
        limit: int = 50,
        before: int | None = None,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        """List photos newest first, optionally for one device and older than `before`."""
        records = self._get_multi(query_instance.did == did) if did else self.table.all()
        photos = cast("list[dict[str, Any]]", list(records))
        if before is not None:
            photos = [photo for photo in photos if (to_int(photo.get("ts"), 0) or 0) < before]
        if kind is not None:
            photos = [photo for photo in photos if photo.get("kind") == kind]
        # The time of a map comes in seconds and the time of a picture in
        # milliseconds, so the times are scaled up before they are compared.
        photos = [{**photo, "ts": to_milliseconds(to_int(photo.get("ts"), 0) or 0)} for photo in photos]
        photos.sort(key=lambda photo: to_int(photo.get("ts"), 0) or 0, reverse=True)
        return photos[:limit]

    def get_by_photo_id(self, photo_id: str) -> dict[str, Any] | None:
        """Return the first record with a matching `id`."""
        for record in self.list_all():
            if record.get("id") == photo_id:
                return record
        _LOGGER.debug(f"No photo found for id={photo_id}")
        return None

    def maps_for_logs(self, logs: list[CleanLog]) -> dict[str, str]:
        """Return the map of every job, keyed by the id of the job.

        The robot uploads the map of a job when the job is done, so the map of a
        job is the one that was uploaded closest to the end of the job.
        """
        uploads: dict[str, list[tuple[int, str]]] = {}
        for photo in self.list_by_did(limit=100, kind=KIND_MAP):
            did = str(photo.get("did", ""))
            uploads.setdefault(did, []).append((to_int(photo.get("ts"), 0) or 0, str(photo.get("id", ""))))

        maps: dict[str, str] = {}
        for did, entries in uploads.items():
            entries.sort()
            jobs = sorted((log for log in logs if log.did == did), key=lambda log: to_int(log.ts, 0) or 0)
            for index, log in enumerate(jobs):
                # The log holds the time in seconds and the map in milliseconds.
                started = (to_int(log.ts, 0) or 0) * 1000
                ended = started + (to_int(log.last, 0) or 0) * 1000
                # The next job starts when this one is over, a map that was
                # uploaded after that belongs to the next job.
                limit: int | None = None
                if index + 1 < len(jobs):
                    limit = (to_int(jobs[index + 1].ts, 0) or 0) * 1000
                candidates = [entry for entry in entries if entry[0] >= started and (limit is None or entry[0] < limit)]
                if not candidates:
                    continue
                closest = min(candidates, key=_distance_from(ended))
                maps[log.clean_log_id] = closest[1]
                entries.remove(closest)
        return maps

    def remove_all(self) -> None:
        """Remove every photo."""
        self.table.truncate()

    def prune(self, did: str, keep: int) -> None:
        """Drop all but the `keep` newest photos of a device."""
        records = self._get_multi(query_instance.did == did)
        photos = sorted(
            records,
            key=lambda photo: to_milliseconds(to_int(photo.get("ts"), 0) or 0),
            reverse=True,
        )
        for photo in photos[keep:]:
            self.table.remove(doc_ids=[photo.doc_id])

    @staticmethod
    def encode_image(data: bytes) -> str:
        """Return base64 form of raw image bytes, for storage in JSON."""
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def decode_image(data: str) -> bytes:
        """Return raw image bytes from their stored base64 form."""
        return base64.b64decode(data.encode("ascii"))

    @staticmethod
    def decode_map(data: str) -> dict[str, Any]:
        """Return the map document of a stored upload, or an empty dict."""
        try:
            parsed = json.loads(PhotoRepo.decode_image(data))
        except (ValueError, UnicodeDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}


def _distance_from(moment: int) -> Callable[[tuple[int, str]], int]:
    """Return a function that tells how far a timestamp is from a moment."""

    def _distance(entry: tuple[int, str]) -> int:
        return abs(entry[0] - moment)

    return _distance
