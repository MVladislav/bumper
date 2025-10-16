"""Token management operations utilizing Token model."""

from datetime import datetime, timedelta
import logging

from tinydb import where
from tinydb.table import Document

from bumper.utils.settings import config as bumper_isc
from bumper.web.models import Token

from .base import BaseRepo
from .db import TABLE_TOKENS, query_instance

_LOGGER = logging.getLogger(__name__)


class TokenRepo(BaseRepo):
    """Data access object for Token records."""

    def __init__(self) -> None:
        super().__init__(TABLE_TOKENS)

    def add(self, userid: str, token_str: str) -> None:
        """Create and insert a new Token for a user."""
        expiration = datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(seconds=bumper_isc.TOKEN_VALIDITY_SECONDS)
        token = Token(userid=userid, token=token_str, expiration=expiration)
        q = (query_instance.userid == userid) & (query_instance.token == token_str)
        if not self.table.contains(q):
            self.table.insert(token.to_db())

    def get(self, user_id: str, token_str: str) -> Token | None:
        """Get Token by user and token string."""
        rec = self._get((query_instance.userid == user_id) & (query_instance.token == token_str))
        return Token.from_dict(rec) if isinstance(rec, dict | Document) else None

    def get_first(self, user_id: str) -> Token | None:
        """Get first Token by user."""
        rec = self._get(query_instance.userid == user_id)
        return Token.from_dict(rec) if isinstance(rec, dict | Document) else None

    def list_for_user(self, user_id: str) -> list[Token]:
        """List all Tokens for user."""
        recs = self.table.search(query_instance.userid == user_id)
        return [Token.from_dict(r) for r in recs]

    def verify(self, user_id: str, token_str: str) -> bool:
        """Verify Token existence."""
        return bool(self.table.contains((query_instance.userid == user_id) & (query_instance.token == token_str)))

    def add_auth_code(self, user_id: str, auth_code: str) -> bool:
        """Add auth code to existing Token."""
        rec = self._get(query_instance.userid == user_id)
        if rec:
            self.table.update({"auth_code": auth_code}, query_instance.userid == user_id)
            return True
        return False

    def add_it_token(self, user_id: str, it_token: str) -> bool:
        """Add IT token to existing Token."""
        rec = self._get(query_instance.userid == user_id)
        if rec:
            self.table.update({"it_token": it_token}, query_instance.userid == user_id)
            return True
        return False

    def get_by_auth_code(self, auth_code: str) -> Token | None:
        """Get Token by auth code."""
        rec = self._get(query_instance.auth_code == auth_code)
        return Token.from_dict(rec) if isinstance(rec, dict | Document) else None

    def verify_it(self, user_id: str, it_token: str) -> bool:
        """Verify IT token existence."""
        return bool(self.table.contains((query_instance.userid == user_id) & (query_instance.it_token == it_token)))

    def verify_auth_code(self, user_id: str, auth_code: str) -> bool:
        """Verify auth code existence."""
        return bool(self.table.contains((query_instance.userid == user_id) & (query_instance.auth_code == auth_code)))

    def login_by_it_token(self, it_token: str) -> Token | None:
        """Login by IT token."""
        rec = self._get(query_instance.it_token == it_token)
        return Token.from_dict(rec) if isinstance(rec, dict | Document) else None

    def revoke_user_expired(self, user_id: str) -> None:
        """Revoke expired Tokens for user."""
        now_iso = datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).isoformat()
        expired = self.table.search((query_instance.userid == user_id) & (where("expiration") < now_iso))
        for r in expired:
            _LOGGER.debug(f"Revoking expired token {r.get('token')}")
            self.table.remove(doc_ids=[r.doc_id])

    def revoke_token(self, user_id: str, token_str: str) -> None:
        """Revoke specific Token for user."""
        self.table.remove((query_instance.userid == user_id) & (query_instance.token == token_str))

    def revoke_expired(self) -> None:
        """Revoke all expired Tokens."""
        now_iso = datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).isoformat()
        expired = self.table.search(where("expiration") < now_iso)
        for r in expired:
            _LOGGER.debug(f"Revoking expired token {r.get('token')}")
            self.table.remove(doc_ids=[r.doc_id])

    def revoke_all_for_user(self, user_id: str) -> None:
        """Revoke all Tokens for user."""
        recs = self.table.search(query_instance.userid == user_id)
        self.table.remove(doc_ids=[r.doc_id for r in recs])
