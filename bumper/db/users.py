"""CRUD operations for BumperUser records."""

from tinydb.table import Document

from bumper.utils.settings import config as bumper_isc
from bumper.web.utils.models import BumperUser

from .base import BaseRepo
from .db import TABLE_USERS, query_instance


class UserRepo(BaseRepo):
    """Data access object for BumperUser."""

    def __init__(self) -> None:
        super().__init__(TABLE_USERS)

    def add(self, user_id: str) -> None:
        """Create a new user if not exists."""
        if not self.get_by_id(user_id):
            user = BumperUser(userid=user_id)
            if len(self._upsert(user.as_dict(), query_instance.userid == user_id)) > 0:
                self.add_home_id(user.userid, bumper_isc.HOME_ID)

    def remove(self, user_id: str) -> None:
        """Remove a user if exists."""
        self._remove(query_instance.userid == user_id)

    def get_by_id(self, user_id: str) -> BumperUser | None:
        """Get user by ID."""
        doc = self._get(query_instance.userid == user_id)
        return BumperUser.from_dict(doc) if isinstance(doc, dict | Document) else None

    def get_by_device_id(self, device_id: str) -> BumperUser | None:
        """Get user by device ID."""
        doc = self._get(query_instance.devices.any([device_id]))
        return BumperUser.from_dict(doc) if isinstance(doc, dict | Document) else None

    def get_by_home_id(self, home_id: str) -> BumperUser | None:
        """Get user by home ID."""
        doc = self._get(query_instance.homeids.any([home_id]))
        return BumperUser.from_dict(doc) if isinstance(doc, dict | Document) else None

    def list_all(self) -> list[BumperUser]:
        """List all users."""
        return [BumperUser.from_dict(doc) for doc in self.table.all() if isinstance(doc, dict)]

    # ******************************************************************************

    def add_device(self, user_id: str, did: str) -> None:
        """Add device to user."""
        q = query_instance.userid == user_id
        self.update_list_field(q, "devices", did, True)

    def remove_device(self, user_id: str, did: str) -> None:
        """Remove device from user."""
        q = query_instance.userid == user_id
        self.update_list_field(q, "devices", did, False)

    def add_bot(self, user_id: str, did: str) -> None:
        """Add bot to user."""
        q = query_instance.userid == user_id
        self.update_list_field(q, "bots", did, True)

    def remove_bot(self, user_id: str, did: str) -> None:
        """Remove bot from user."""
        q = query_instance.userid == user_id
        self.update_list_field(q, "bots", did, False)

    def add_home_id(self, user_id: str, did: str) -> None:
        """Add home_id to user."""
        q = query_instance.userid == user_id
        self.update_list_field(q, "homeids", did, True)

    def remove_home_id(self, user_id: str, did: str) -> None:
        """Remove home_id from user."""
        q = query_instance.userid == user_id
        self.update_list_field(q, "homeids", did, False)
