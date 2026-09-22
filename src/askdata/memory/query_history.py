"""Query history — in-memory ring buffer for the current session."""
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List


class QueryHistory:
    """Keeps the last N query/result pairs in memory.

    Production deployments should persist to Redis or a SQL table.
    """

    def __init__(self, max_size: int = 100):
        self._buffer: Deque[Dict[str, Any]] = deque(maxlen=max_size)

    def add(self, query: str, result: Dict[str, Any], user_id: str = "anonymous") -> None:
        self._buffer.append(
            {
                "ts": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "query": query,
                "sql": result.get("sql"),
                "row_count": result.get("row_count"),
                "error": result.get("error"),
            }
        )

    def recent(self, n: int = 10) -> List[Dict[str, Any]]:
        return list(self._buffer)[-n:]

    def clear(self) -> None:
        self._buffer.clear()
