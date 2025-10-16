"""Bot management operations."""

import logging
from typing import Any

from tinydb.table import Document

from bumper.web import models

from .base import BaseRepo
from .db import TABLE_BOTS, query_instance
from .helpers import warn_if_not_doc

_LOGGER = logging.getLogger(__name__)


class BotRepo(BaseRepo):
    """DAO for bot records."""

    def __init__(self) -> None:
        super().__init__(TABLE_BOTS)

    def add(self, name: str, did: str, class_id: str, resource: str, company: str) -> None:
        """Add a new bot."""
        q = query_instance.did == did
        if not self._get(q):
            bot = models.VacBotDevice(did=did, name=name, resource=resource, company=company)
            bot.class_id = class_id
            self._upsert(bot.as_dict(), q)

    def get(self, did: str) -> models.VacBotDevice | None:
        """Get bot by device ID."""
        rec = self._get(query_instance.did == did)
        return models.VacBotDevice.from_dict(rec) if isinstance(rec, dict | Document) else None

    def list_all(self) -> list[models.VacBotDevice]:
        """List all bots."""
        bots = []
        for rec in self.table.all():
            warn_if_not_doc(rec, "BotRepo.list_all entry")
            bots.append(models.VacBotDevice.from_dict(rec))
        return bots

    def remove(self, did: str) -> None:
        """Remove a bot by device ID."""
        self._remove(query_instance.did == did)

    def set_nick(self, did: str | None, nick: str) -> None:
        """Set bot nickname."""
        self._set_field(did, "nick", nick)

    def set_mqtt(self, did: str | None, mqtt: bool) -> None:
        """Set MQTT connection status."""
        self._set_field(did, "mqtt_connection", mqtt)

    def set_xmpp(self, did: str | None, xmpp: bool) -> None:
        """Set XMPP connection status."""
        self._set_field(did, "xmpp_connection", xmpp)

    def reset_all_connections(self) -> None:
        """Reset all bots connection statuses."""
        for rec in self.table.all():
            bot_id = rec.get("did")
            self.set_mqtt(bot_id, False)
            self.set_xmpp(bot_id, False)

    def _set_field(self, did: str | None, field: str, value: Any) -> None:
        """Set a specific field for a bot."""
        if did is None:
            _LOGGER.warning(f"Failed to updated field as did is not set for :: DID: {did} :: field: {field} :: value: {value}")
            return
        self._upsert({field: value}, query_instance.did == did)
