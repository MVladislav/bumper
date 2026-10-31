"""Client management operations.

A client is one app installation or one transport connection of an account.
An account can have several clients, so a row is keyed by the account and the
resource of the client rather than by the account alone.
"""

from collections.abc import Callable

from tinydb.table import Document

from bumper.web.utils import models

from .base import BaseRepo
from .db import TABLE_CLIENTS, query_instance
from .helpers import warn_if_not_doc


class ClientRepo(BaseRepo):
    """DAO for client records."""

    def __init__(self, user_lookup: Callable[[str], models.BumperUser | None] | None = None) -> None:
        super().__init__(TABLE_CLIENTS)
        self._user_lookup = user_lookup

    def add(
        self,
        name: str | None,
        user_id: str,
        realm: str,
        resource: str,
        *,
        client_id: str = "",
        device_id: str = "",
    ) -> None:
        """Add or update one client of an account."""
        canonical = self._canonical_user_id(user_id) or user_id
        rec = self._find_row(
            canonical,
            resource=resource or "",
            client_id=client_id,
            other_user_id=user_id,
        )
        if rec is None:
            client = models.VacBotClient(
                name=name or "",
                userid=canonical,
                realm=realm or "",
                resource=resource or "",
                client_id=client_id,
                device_id=device_id,
            )
            self.table.insert(client.as_dict())
            return

        if rec.get("userid") != canonical:
            target = self._find_row(
                canonical,
                resource=rec.get("resource") or "",
                client_id=client_id or rec.get("client_id") or "",
            )
            if target is not None and target.doc_id != rec.doc_id:
                self._merge_into(target, rec)
                rec = target
            else:
                self.table.update({"userid": canonical}, doc_ids=[rec.doc_id])

        updates: dict[str, str] = {}
        if name:
            updates["name"] = name
        if realm:
            updates["realm"] = realm
        if resource:
            updates["resource"] = resource
        if client_id:
            updates["client_id"] = client_id
        if device_id:
            updates["device_id"] = device_id
        if updates:
            self.table.update(updates, doc_ids=[rec.doc_id])

    def get(
        self,
        user_id: str,
        *,
        resource: str | None = None,
        client_id: str | None = None,
    ) -> models.VacBotClient | None:
        """Get one client by an account name and optionally its resource."""
        canonical = self._canonical_user_id(user_id) or user_id
        rec = self._find_row(
            canonical,
            resource=resource,
            client_id=client_id,
            other_user_id=user_id,
        )
        return models.VacBotClient.from_dict(rec) if isinstance(rec, Document) else None

    def get_by_client_id(self, client_id: str) -> models.VacBotClient | None:
        """Get a client by the id of the app installation."""
        if not client_id:
            return None
        rec = self._get(query_instance.client_id == client_id)
        return models.VacBotClient.from_dict(rec) if isinstance(rec, Document) else None

    def list_all(self) -> list[models.VacBotClient]:
        """List all clients."""
        clients = []
        for rec in self.table.all():
            warn_if_not_doc(rec, "ClientRepo.list_all entry")
            clients.append(models.VacBotClient.from_dict(rec))
        return clients

    def list_for_user(self, user_id: str) -> list[models.VacBotClient]:
        """List every client of one account."""
        canonical = self._canonical_user_id(user_id) or user_id
        return [
            models.VacBotClient.from_dict(rec)
            for rec in self.table.all()
            if isinstance(rec, Document) and self._belongs_to(rec, canonical, user_id)
        ]

    def remove(
        self,
        user_id: str,
        *,
        resource: str | None = None,
        client_id: str | None = None,
        device_id: str | None = None,
    ) -> None:
        """Remove one client, or every client of an account."""
        canonical = self._canonical_user_id(user_id) or user_id
        if resource is not None or client_id is not None or device_id is not None:
            rec = self._find_row(
                canonical,
                resource=resource,
                client_id=client_id,
                device_id=device_id,
                other_user_id=user_id,
            )
            if rec is not None:
                self.table.remove(doc_ids=[rec.doc_id])
            return

        for rec in list(self.table.all()):
            if isinstance(rec, Document) and self._belongs_to(rec, canonical, user_id):
                self.table.remove(doc_ids=[rec.doc_id])

    def reassign_user(self, old_user_id: str, new_user_id: str) -> None:
        """Move every client of a merged account onto the account that remains."""
        if not old_user_id or not new_user_id or old_user_id == new_user_id:
            return

        rows = [rec for rec in self.table.all() if isinstance(rec, Document) and rec.get("userid") == old_user_id]
        for source in rows:
            target = self._find_row(
                new_user_id,
                resource=source.get("resource") or "",
                client_id=source.get("client_id") or "",
            )
            if target is None or target.doc_id == source.doc_id:
                self.table.update({"userid": new_user_id}, doc_ids=[source.doc_id])
                continue
            self._merge_into(target, source)

    def set_mqtt(self, user_id: str | None, mqtt: bool, *, resource: str | None = None) -> None:
        """Set the MQTT status of one client."""
        rec = self._record(user_id, resource)
        if rec is not None:
            self.table.update({"mqtt_connection": mqtt}, doc_ids=[rec.doc_id])

    def set_xmpp(self, user_id: str | None, xmpp: bool, *, resource: str | None = None) -> None:
        """Set the XMPP status of one client."""
        rec = self._record(user_id, resource)
        if rec is not None:
            self.table.update({"xmpp_connection": xmpp}, doc_ids=[rec.doc_id])

    def reset_all_connections(self) -> None:
        """Reset the connection status of every client."""
        for rec in self.table.all():
            if isinstance(rec, Document):
                self.table.update(
                    {"mqtt_connection": False, "xmpp_connection": False},
                    doc_ids=[rec.doc_id],
                )

    def reconcile(self, users: list[models.BumperUser]) -> None:
        """Move clients onto their account and drop names no account owns."""
        known = {user.userid for user in users}
        owners = {name: user.userid for user in users for name in user.names}

        for client in self.list_all():
            if client.userid in known:
                continue
            target = owners.get(client.userid)
            if target is None:
                self.remove(client.userid)
            else:
                self.reassign_user(client.userid, target)

    def _record(self, user_id: str | None, resource: str | None) -> Document | None:
        """Return the row a status update names."""
        if user_id is None:
            return None
        canonical = self._canonical_user_id(user_id) or user_id
        return self._find_row(canonical, resource=resource, other_user_id=user_id)

    def _find_row(
        self,
        user_id: str,
        *,
        resource: str | None = None,
        client_id: str | None = None,
        device_id: str | None = None,
        other_user_id: str | None = None,
    ) -> Document | None:
        """Find one client row of an account.

        A name of the account and the name the caller presented are both
        accepted, because a row written before a merge can still carry the old
        name. A resource or a client id narrows the row; without either, the
        first row of the account is returned.
        """
        names = {user_id}
        if other_user_id is not None:
            names.add(other_user_id)
        rows = []
        for rec in self.table.all():
            owner = rec.get("userid")
            if owner in names or (isinstance(owner, str) and self._canonical_user_id(owner) in names):
                rows.append(rec)
        if client_id:
            for rec in rows:
                if rec.get("client_id") == client_id:
                    return rec
            if not resource and not device_id:
                return None
            for rec in rows:
                if (
                    (resource is None or rec.get("resource") == resource)
                    and (device_id is None or rec.get("device_id") == device_id)
                    and not rec.get("client_id")
                ):
                    return rec
            return None
        if resource is not None:
            for rec in rows:
                if rec.get("resource") == resource and (device_id is None or rec.get("device_id") == device_id):
                    return rec
            return None
        if device_id is not None:
            for rec in rows:
                if rec.get("device_id") == device_id:
                    return rec
            return None
        return rows[0] if rows else None

    def _canonical_user_id(self, user_id: str) -> str | None:
        """Return the account a name belongs to, when Bumper already knows it."""
        if self._user_lookup is None:
            return None
        user = self._user_lookup(user_id)
        return user.userid if user is not None else None

    def _belongs_to(self, rec: Document, canonical: str, presented: str) -> bool:
        """Return whether a client row belongs to the account that is named."""
        owner = rec.get("userid")
        if owner in {canonical, presented}:
            return True
        return isinstance(owner, str) and self._canonical_user_id(owner) == canonical

    def _merge_into(self, target: Document, source: Document) -> None:
        """Fold one client row into the row that remains and remove the other."""
        merged = models.VacBotClient.from_dict(target)
        moved = models.VacBotClient.from_dict(source)
        merged.name = merged.name or moved.name
        merged.realm = merged.realm or moved.realm
        merged.resource = merged.resource or moved.resource
        merged.client_id = merged.client_id or moved.client_id
        merged.device_id = merged.device_id or moved.device_id
        merged.mqtt_connection = merged.mqtt_connection or moved.mqtt_connection
        merged.xmpp_connection = merged.xmpp_connection or moved.xmpp_connection
        self.table.update(merged.as_dict(), doc_ids=[target.doc_id])
        self.table.remove(doc_ids=[source.doc_id])
