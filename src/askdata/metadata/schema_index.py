"""Schema index — lightweight in-memory search over table/column metadata."""
from typing import Any, Dict, List

from ..connectors.base import BaseConnector


class SchemaIndex:
    """Indexes the database schema and lets the agent look up relevant tables.

    The search is intentionally simple (keyword match). For production scale
    swap it with embeddings + a vector store.
    """

    def __init__(self, connector: BaseConnector):
        self.connector = connector
        self._schema: List[Dict[str, Any]] = []
        self.refresh()

    def refresh(self) -> None:
        self._schema = self.connector.get_schema()

    def _score(self, query: str, text: str) -> int:
        query_lower = query.lower()
        text_lower = text.lower()
        score = 0
        for token in query_lower.split():
            if token in text_lower:
                score += 1
        return score

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        scored = []
        for row in self._schema:
            text = f"{row.get('table_name', '')} {row.get('column_name', '')}"
            s = self._score(query, text)
            if s > 0:
                scored.append((s, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]
