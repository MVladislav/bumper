"""CRUD operations for BumperUser records."""

from tinydb.table import Document

from bumper.utils.account_ids import is_account_uid, is_iot_uid, new_account_uid, new_iot_uid, new_uc_uid
from bumper.utils.settings import config as bumper_isc
from bumper.web.utils.models import BumperUser

from .base import BaseRepo
from .db import TABLE_USERS, query_instance


class UserRepo(BaseRepo):
    """Data access object for BumperUser."""

    def __init__(self) -> None:
        super().__init__(TABLE_USERS)

    def add(self, user_id: str) -> None:
        """Create a new user if not exists.

        The caller may pass any name, including the id of an account created
        by an older version. The public account names are filled in when the
        account is used, so an old record keeps working.
        """
        if not self.get_by_id(user_id):
            user = BumperUser(userid=user_id)
            if is_account_uid(user_id):
                user.account_uid = user_id
            if is_iot_uid(user_id):
                user.iot_uid = user_id
            if len(self._upsert(user.as_dict(), query_instance.userid == user_id)) > 0:
                self.add_home_id(user.userid, bumper_isc.DEFAULT_HOME_ID)

    def create(self, login_name: str, username: str | None = None, email: str | None = None) -> BumperUser:
        """Create an account with the names the API assigns.

        The account id does not come from the login name. The login name is
        stored beside it, so the same account is found again when the same
        name is used, and a different name does not create a second record.
        """
        account_uid = new_account_uid()
        user = BumperUser(userid=account_uid)
        user.account_uid = account_uid
        user.uc_uid = new_uc_uid()
        user.iot_uid = new_iot_uid()
        user.login_name = login_name
        user.username = username or login_name or bumper_isc.USER_USERNAME_DEFAULT
        user.email = email
        user.aliases = [user.uc_uid, user.iot_uid]
        self.table.insert(user.as_dict())
        self.add_home_id(user.userid, bumper_isc.DEFAULT_HOME_ID)
        return user

    def remove(self, user_id: str) -> None:
        """Remove a user if exists."""
        user = self.get_by_id(user_id)
        if user is not None:
            self._remove(query_instance.userid == user.userid)

    def _get_exact(self, user_id: str) -> BumperUser | None:
        """Get the user whose own id is the given id."""
        doc = self._get(query_instance.userid == user_id)
        return BumperUser.from_dict(doc) if isinstance(doc, dict | Document) else None

    def get_by_id(self, user_id: str) -> BumperUser | None:
        """Get a user by any name that points at the account."""
        if (user := self._get_exact(user_id)) is not None:
            return user
        for field in ("account_uid", "uc_uid", "iot_uid"):
            doc = self._get(getattr(query_instance, field) == user_id)
            if isinstance(doc, dict | Document):
                return BumperUser.from_dict(doc)
        doc = self._get(query_instance.aliases.any([user_id]))
        return BumperUser.from_dict(doc) if isinstance(doc, dict | Document) else None

    def get_by_login_name(self, login_name: str) -> BumperUser | None:
        """Get the account that logs in with a name, ignoring case."""
        wanted = login_name.casefold()
        matches = [user for user in self.list_all() if user.login_name and user.login_name.casefold() == wanted]
        matches.sort(key=lambda user: self._created_order(user.userid))
        return matches[0] if matches else None

    def _get_all_by_device_id(self, device_id: str) -> list[BumperUser]:
        """Get every user that carries the app device id, oldest first."""
        docs = self._get_multi(query_instance.devices.any([device_id]))
        docs.sort(key=lambda doc: doc.doc_id)
        return [BumperUser.from_dict(doc) for doc in docs]

    def get_by_device_id(self, device_id: str) -> BumperUser | None:
        """Get the oldest user that carries the app device id."""
        users = self._get_all_by_device_id(device_id)
        return users[0] if users else None

    def get_by_home_id(self, home_id: str) -> BumperUser | None:
        """Get user by home ID."""
        doc = self._get(query_instance.homeids.any([home_id]))
        return BumperUser.from_dict(doc) if isinstance(doc, dict | Document) else None

    def list_all(self) -> list[BumperUser]:
        """List all users."""
        return [BumperUser.from_dict(doc) for doc in self.table.all() if isinstance(doc, dict)]

    def merge(self, first: BumperUser, second: BumperUser) -> tuple[BumperUser, str]:
        """Merge two records of one account and return the older record and the removed id."""
        if first.userid == second.userid:
            return first, ""

        if self._created_order(first.userid) <= self._created_order(second.userid):
            primary, other = first, second
        else:
            primary, other = second, first

        merged = BumperUser.from_dict(primary.as_dict())
        merged.aliases = self._union(
            merged.aliases,
            other.aliases,
            [other.userid, other.account_uid, other.uc_uid, other.iot_uid],
        )
        merged.devices = self._union(merged.devices, other.devices)
        merged.bots = self._union(merged.bots, other.bots)
        merged.homeids = self._union(merged.homeids, other.homeids)

        device_names = dict(other.device_names)
        device_names.update(merged.device_names)
        merged.device_names = device_names

        merged.account_uid = merged.account_uid or other.account_uid
        merged.uc_uid = merged.uc_uid or other.uc_uid
        merged.iot_uid = merged.iot_uid or other.iot_uid
        merged.login_name = merged.login_name or other.login_name
        merged.email = merged.email or other.email
        merged.backup_email = merged.backup_email or other.backup_email
        if merged.username == bumper_isc.USER_USERNAME_DEFAULT:
            merged.username = other.username
        if merged.nickname == bumper_isc.USER_NICKNAME_DEFAULT:
            merged.nickname = other.nickname
        if merged.device_verification == "DISABLED":
            merged.device_verification = other.device_verification

        self.table.remove(query_instance.userid == other.userid)
        self._upsert(merged.as_dict(), query_instance.userid == primary.userid)
        return merged, other.userid

    def add_alias(self, user_id: str, alias: str) -> None:
        """Remember an alternate name of the same account."""
        user = self._get_exact(user_id)
        if user is None or not alias or alias == user.userid or alias in user.aliases:
            return
        aliases = [*user.aliases, alias]
        self._upsert({"aliases": aliases}, query_instance.userid == user.userid)

    def bind_device(self, user_id: str, device_id: str) -> None:
        """Bind an app device to one user and unbind it from every other user."""
        user = self.get_by_id(user_id)
        if user is None or not device_id:
            return

        for candidate in self._get_all_by_device_id(device_id):
            if candidate.userid == user.userid:
                continue
            devices = [device for device in candidate.devices if device != device_id]
            self._upsert({"devices": devices}, query_instance.userid == candidate.userid)
            if device_id in candidate.device_names:
                device_names = dict(candidate.device_names)
                del device_names[device_id]
                self._upsert({"device_names": device_names}, query_instance.userid == candidate.userid)

        self.add_device(user.userid, device_id)

    def add_device(self, user_id: str, did: str) -> None:
        """Add device to user."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self.update_list_field(query_instance.userid == canonical, "devices", did, True)

    def remove_device(self, user_id: str, did: str) -> None:
        """Remove device from user."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        q = query_instance.userid == canonical
        self.update_list_field(q, "devices", did, False)
        user = self._get_exact(canonical)
        if user is not None and did in user.device_names:
            device_names = dict(user.device_names)
            del device_names[did]
            self._upsert({"device_names": device_names}, q)

    def set_device_name(self, user_id: str, device_id: str, name: str) -> None:
        """Store the reported name of an app device on its account."""
        user = self.get_by_id(user_id)
        if user is None or device_id not in user.devices:
            return
        device_names = dict(user.device_names)
        device_names[device_id] = name
        self._upsert({"device_names": device_names}, query_instance.userid == user.userid)

    def set_device_verification(self, user_id: str, value: str) -> None:
        """Store whether a new device has to verify itself with a passcode."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self._upsert({"device_verification": value}, query_instance.userid == canonical)

    def set_identity(self, user: BumperUser) -> None:
        """Store the public names and the login name of an account."""
        self._upsert(
            {
                "account_uid": user.account_uid,
                "uc_uid": user.uc_uid,
                "iot_uid": user.iot_uid,
                "login_name": user.login_name,
                "aliases": user.aliases,
            },
            query_instance.userid == user.userid,
        )

    def set_login_name(self, user_id: str, login_name: str) -> None:
        """Store the name the account logs in with."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self._upsert({"login_name": login_name}, query_instance.userid == canonical)

    def set_email(self, user_id: str, email: str) -> None:
        """Store the address the account is registered with."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self._upsert({"email": email}, query_instance.userid == canonical)

    def set_backup_email(self, user_id: str, email: str) -> None:
        """Store the address the account can be recovered with."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self._upsert({"backup_email": email}, query_instance.userid == canonical)

    def add_bot(self, user_id: str, did: str) -> None:
        """Add bot to user."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self.update_list_field(query_instance.userid == canonical, "bots", did, True)

    def remove_bot(self, user_id: str, did: str) -> None:
        """Remove bot from user."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self.update_list_field(query_instance.userid == canonical, "bots", did, False)

    def add_home_id(self, user_id: str, did: str) -> None:
        """Add home_id to user."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self.update_list_field(query_instance.userid == canonical, "homeids", did, True)

    def remove_home_id(self, user_id: str, did: str) -> None:
        """Remove home_id from user."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self.update_list_field(query_instance.userid == canonical, "homeids", did, False)

    def set_nickname(self, user_id: str, nickname: str) -> None:
        """Set the display name of a user."""
        canonical = self._canonical_id(user_id)
        if canonical is None:
            return
        self._upsert({"nickname": nickname}, query_instance.userid == canonical)

    def _canonical_id(self, user_id: str) -> str | None:
        """Return the id of the user record an alternate name points at."""
        user = self.get_by_id(user_id)
        return user.userid if user is not None else None

    def _created_order(self, user_id: str) -> int:
        """Return the insertion order of a user record."""
        doc = self._get(query_instance.userid == user_id)
        return doc.doc_id if isinstance(doc, Document) else 2**63

    @staticmethod
    def _union(*values: list[str]) -> list[str]:
        """Merge lists while keeping the first occurrence of every item."""
        merged: list[str] = []
        for value in values:
            for item in value:
                if item and item not in merged:
                    merged.append(item)
        return merged
