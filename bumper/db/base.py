"""Provide base repository with common TinyDB operations."""

from typing import Any

from tinydb.queries import QueryLike
from tinydb.table import Document, Table

from .db import get_db
from .helpers import warn_if_not_doc


class BaseRepo:
    """Abstract base class for table-specific repos."""

    def __init__(self, table_name: str) -> None:
        self._table_name: str = table_name

    @property
    def table(self) -> Table:
        """Return the TinyDB table for this repo."""
        return get_db().table(self._table_name)

    def _upsert(self, data: dict[str, Any] | None, query: QueryLike) -> list[int]:
        """Insert or update a record."""
        if data is None:
            return []
        return self.table.upsert(data, query)

    def _get(self, query: QueryLike) -> Document | None:
        """Retrieve a document matching the query."""
        rec = self.table.get(query)
        warn_if_not_doc(rec, f"{self._table_name}.get result ({query.__dict__})")
        return rec if isinstance(rec, dict | Document) else None

    def _get_multi(self, query: QueryLike) -> list[Document]:
        """Retrieve a document or list of documents matching the query."""
        return self.table.search(query)

    def _remove(self, query: QueryLike) -> None:
        """Remove a document matching the query."""
        rec = self.table.get(query)
        if isinstance(rec, Document):
            self.table.remove(doc_ids=[rec.doc_id])

    def update_list_field(self, query: QueryLike, field: str, value: Any, add: bool) -> bool:
        """Add or remove an item in a list field."""
        rec = self._get(query)
        if not isinstance(rec, Document):
            return False
        lst = list(rec.get(field, []))
        if add and value not in lst:
            lst.append(value)
        elif not add and value in lst:
            lst.remove(value)
        return len(self._upsert({field: lst}, query)) > 0
