"""Excel connector stub — implement when needed."""
from typing import Any, Dict, List

from .base import BaseConnector


class ExcelConnector(BaseConnector):
    name = "excel"

    def execute_readonly(self, sql: str, params: List[Any] | None = None) -> List[Dict[str, Any]]:
        raise NotImplementedError("Excel connector is a planned extension — see docs/roadmap.md")

    def get_schema(self) -> List[Dict[str, Any]]:
        raise NotImplementedError
