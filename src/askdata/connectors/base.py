"""Connector base class — every datasource implements this contract."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseConnector(ABC):
    """Read-only data source connector.

    All concrete connectors must guarantee that `execute_readonly` only runs
    safe SELECT/WITH statements and never mutates the source.
    """

    name: str = "base"

    @abstractmethod
    def execute_readonly(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Run a read-only query and return rows as list of dicts."""

    @abstractmethod
    def get_schema(self) -> List[Dict[str, Any]]:
        """Return table/column metadata for the connected source."""

    def get_sample(self, table: str, n: int = 3) -> List[Dict[str, Any]]:
        """Return N sample rows from a table."""
        sql = f"SELECT * FROM {table} LIMIT {n}"
        return self.execute_readonly(sql)

    def close(self) -> None:  # pragma: no cover - default no-op
        pass
