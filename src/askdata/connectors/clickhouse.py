"""ClickHouse connector stub — implement when needed."""
from typing import Any, Dict, List

from .base import BaseConnector


class ClickHouseConnector(BaseConnector):
    name = "clickhouse"

    def execute_readonly(self, sql: str, params: List[Any] | None = None) -> List[Dict[str, Any]]:
        raise NotImplementedError("ClickHouse connector is a planned extension — see docs/roadmap.md")

    def get_schema(self) -> List[Dict[str, Any]]:
        raise NotImplementedError
