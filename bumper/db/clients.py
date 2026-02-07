"""Client management operations."""

import logging

from tinydb.table import Document

from bumper.web.utils import models

from .base import BaseRepo
from .db import TABLE_CLIENTS, query_instance
from .helpers import warn_if_not_doc

_LOGGER = logging.getLogger(__name__)


class ClientRepo(BaseRepo):
    """DAO for client records."""

    def __init__(self) -> None:
        super().__init__(TABLE_CLIENTS)

    def add(self, name: str | None, user_id: str, realm: str, resource: str) -> None:
        """Add a new client."""
        q = query_instance.userid == user_id
        if not self._get(q):
            client = models.VacBotClient(name=name or "", userid=user_id, realm=realm, resource=resource)
            self._upsert(client.as_dict(), q)

    def get(self, user_id: str) -> models.VacBotClient | None:
        """Get client by user ID."""
        rec = self._get(query_instance.userid == user_id)
        return models.VacBotClient.from_dict(rec) if isinstance(rec, dict | Document) else None

    def list_all(self) -> list[models.VacBotClient]:
        """List all clients."""
        clients = []
        for rec in self.table.all():
            warn_if_not_doc(rec, "ClientRepo.list_all entry")
            clients.append(models.VacBotClient.from_dict(rec))
        return clients

    def remove(self, user_id: str) -> None:
        """Remove a client by user ID."""
        self._remove(query_instance.userid == user_id)

    def set_mqtt(self, user_id: str | None, mqtt: bool) -> None:
        """Set MQTT connection status."""
        self._upsert({"mqtt_connection": mqtt}, query_instance.userid == user_id)

    def set_xmpp(self, user_id: str | None, xmpp: bool) -> None:
        """Set XMPP connection status."""
        self._upsert({"xmpp_connection": xmpp}, query_instance.userid == user_id)

    def reset_all_connections(self) -> None:
        """Reset all clients' connection statuses."""
        for rec in self.table.all():
            user = rec.get("userid")
            self.set_mqtt(user, False)
            self.set_xmpp(user, False)
