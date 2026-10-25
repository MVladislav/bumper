"""Token management operations utilizing Token model."""

from datetime import datetime, timedelta
import logging

from tinydb import where
from tinydb.table import Document

from bumper.utils.settings import config as bumper_isc
from bumper.web.utils.models import Token

from .base import BaseRepo
from .db import TABLE_TOKENS, query_instance

_LOGGER = logging.getLogger(__name__)


class TokenRepo(BaseRepo):
    """Data access object for Token records."""

    def __init__(self) -> None:
        super().__init__(TABLE_TOKENS)

    def add(
        self,
        userid: str,
        token_str: str,
        *,
        client_id: str | None = None,
        resource: str | None = None,
        device_id: str | None = None,
    ) -> None:
        """Create and insert a new Token for a client of a user."""
        expiration = datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(seconds=bumper_isc.TOKEN_VALIDITY_SECONDS)
        token = Token(
            userid=userid,
            token=token_str,
            expiration=expiration,
            client_id=client_id,
            resource=resource,
            device_id=device_id,
        )
        q = (query_instance.userid == userid) & (query_instance.token == token_str)
        if not self.table.contains(q):
            self.table.insert(token.to_db())

    def get(self, user_id: str, token_str: str) -> Token | None:
        """Get Token by user and token string."""
        rec = self._get((query_instance.userid == user_id) & (query_instance.token == token_str))
        return Token.from_dict(rec) if isinstance(rec, dict | Document) else None

    def get_by_token(self, token_str: str) -> Token | None:
        """Get the token row a portal token names."""
        rec = self._get(query_instance.token == token_str)
        return Token.from_dict(rec) if isinstance(rec, dict | Document) else None

    def get_by_it_token(self, it_token: str) -> Token | None:
        """Get the token row an IT token names."""
        rec = self._get(query_instance.it_token == it_token)
        return Token.from_dict(rec) if isinstance(rec, dict | Document) else None

    def get_by_client_id(self, client_id: str) -> Token | None:
        """Get the newest token row of an app client."""
        if not client_id:
            return None
        rows = self._get_multi(query_instance.client_id == client_id)
        if not rows:
            return None
        rows.sort(key=lambda row: row.doc_id, reverse=True)
        return Token.from_dict(rows[0])

    def get_first(self, user_id: str) -> Token | None:
        """Get first Token by user."""
        rec = self._get_first(query_instance.userid == user_id)
        return Token.from_dict(rec) if isinstance(rec, dict | Document) else None

    def list_for_user(self, user_id: str) -> list[Token]:
        """List all Tokens for user."""
        recs = self._get_multi(query_instance.userid == user_id)
        return [Token.from_dict(r) for r in recs]

    def verify(self, user_id: str, token_str: str) -> bool:
        """Verify Token existence."""
        return self._valid(self.get(user_id, token_str)) is not None

    def get_valid_by_token(self, token_str: str) -> Token | None:
        """Get the portal token row of a secret that has not expired."""
        return self._valid(self.get_by_token(token_str))

    def add_auth_code(self, user_id: str, auth_code: str) -> bool:
        """Add an auth code to the first Token of a user."""
        rec = self._get_first(query_instance.userid == user_id)
        if rec is None:
            return False
        return self.add_auth_code_to_token(str(rec.get("token") or ""), auth_code)

    def add_auth_code_to_token(self, token_str: str, auth_code: str) -> bool:
        """Attach an auth code to one portal token row."""
        if not token_str or self._get(query_instance.token == token_str) is None:
            return False
        return len(self._upsert({"auth_code": auth_code}, query_instance.token == token_str)) > 0

    def add_auth_code_for_it_token(
        self,
        it_token: str,
        auth_code: str,
        *,
        client_id: str | None = None,
        resource: str | None = None,
    ) -> bool:
        """Attach an auth code and the client names to the row of an IT token."""
        row = self._get(query_instance.it_token == it_token)
        if row is None:
            return False
        updates: dict[str, str | None] = {"auth_code": auth_code}
        if client_id is not None:
            updates["client_id"] = client_id
        if resource is not None:
            updates["resource"] = resource
        return len(self._upsert(updates, query_instance.it_token == it_token)) > 0

    def add_it_token(self, user_id: str, it_token: str) -> bool:
        """Add an IT token to the first Token of a user."""
        rec = self._get_first(query_instance.userid == user_id)
        if rec is None:
            return False
        query = (query_instance.userid == user_id) & (query_instance.token == rec.get("token"))
        return len(self._upsert({"it_token": it_token}, query)) > 0

    def add_it_token_to_token(self, token_str: str, it_token: str) -> bool:
        """Attach an IT token to the row of a portal token."""
        if self._get(query_instance.token == token_str) is None:
            return False
        return len(self._upsert({"it_token": it_token}, query_instance.token == token_str)) > 0

    def set_client_for_it_token(
        self,
        it_token: str,
        *,
        client_id: str | None = None,
        resource: str | None = None,
    ) -> None:
        """Store the client names the new-auth request names."""
        updates: dict[str, str] = {}
        if client_id is not None:
            updates["client_id"] = client_id
        if resource is not None:
            updates["resource"] = resource
        if updates:
            self._upsert(updates, query_instance.it_token == it_token)

    def get_by_auth_code(self, auth_code: str) -> Token | None:
        """Get Token by auth code."""
        rec = self._get_first(query_instance.auth_code == auth_code)
        return Token.from_dict(rec) if isinstance(rec, dict | Document) else None

    def extend_oauth_session(self, auth_code: str, expiration: datetime) -> bool:
        """Keep a portal token row until the refresh token for it expires."""
        rec = self._get_first(query_instance.auth_code == auth_code)
        if rec is None:
            return False
        return bool(self.table.update({"expiration": expiration.isoformat()}, doc_ids=[rec.doc_id]))

    def get_by_secret(self, secret: str) -> Token | None:
        """Get the token row that carries any secret Bumper issued."""
        if not secret:
            return None
        for field in ("token", "auth_code", "it_token"):
            rec = self._get_first(getattr(query_instance, field) == secret)
            if isinstance(rec, dict | Document):
                return Token.from_dict(rec)
        return None

    def get_valid_by_secret(self, secret: str) -> Token | None:
        """Get the token row of a secret that has not expired."""
        return self._valid(self.get_by_secret(secret))

    def verify_it(self, user_id: str, it_token: str) -> bool:
        """Verify IT token existence."""
        return bool(self.table.contains((query_instance.userid == user_id) & (query_instance.it_token == it_token)))

    def verify_auth_code(self, user_id: str, auth_code: str) -> bool:
        """Verify auth code existence."""
        return bool(self.table.contains((query_instance.userid == user_id) & (query_instance.auth_code == auth_code)))

    def login_by_it_token(self, it_token: str) -> Token | None:
        """Get the live token row of an IT token."""
        return self._valid(self.get_by_it_token(it_token))

    def revoke_user_expired(self, user_id: str) -> None:
        """Revoke expired Tokens for user."""
        now_iso = datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).isoformat()
        expired = self._get_multi((query_instance.userid == user_id) & (where("expiration") < now_iso))
        for r in expired:
            _LOGGER.debug(f"Revoking expired token {r.get('token')}")
            self.table.remove(doc_ids=[r.doc_id])

    def revoke_token(self, user_id: str, token_str: str) -> None:
        """Revoke specific Token for user."""
        self.table.remove((query_instance.userid == user_id) & (query_instance.token == token_str))

    def revoke_expired(self) -> None:
        """Revoke all expired Tokens."""
        now_iso = datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).isoformat()
        expired = self._get_multi(where("expiration") < now_iso)
        for r in expired:
            _LOGGER.debug(f"Revoking expired token {r.get('token')}")
            self.table.remove(doc_ids=[r.doc_id])

    def revoke_all_for_user(self, user_id: str) -> None:
        """Revoke all Tokens for user."""
        recs = self._get_multi(query_instance.userid == user_id)
        self.table.remove(doc_ids=[r.doc_id for r in recs])

    def reassign_user(self, old_user_id: str, new_user_id: str) -> None:
        """Move the tokens of a merged user onto the account that remains."""
        if not old_user_id or not new_user_id or old_user_id == new_user_id:
            return

        old_rows = self._get_multi(query_instance.userid == old_user_id)
        if not old_rows:
            return

        for row in old_rows:
            token_str = row.get("token")
            existing = self._get((query_instance.userid == new_user_id) & (query_instance.token == token_str))
            if existing is None:
                self.table.update({"userid": new_user_id}, doc_ids=[row.doc_id])
                continue

            updates = {}
            for field in ("auth_code", "it_token", "client_id", "resource", "device_id"):
                if not existing.get(field) and row.get(field):
                    updates[field] = row.get(field)
            if updates:
                self._upsert(updates, (query_instance.userid == new_user_id) & (query_instance.token == token_str))
            self.table.remove(doc_ids=[row.doc_id])

    @staticmethod
    def _valid(token: Token | None) -> Token | None:
        """Return a token row only while it has not expired."""
        if token is None:
            return None
        expiration = token.expiration
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=bumper_isc.LOCAL_TIMEZONE)
        return token if expiration > datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) else None
