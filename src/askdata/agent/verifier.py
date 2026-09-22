"""SQL self-correction — LLM-driven SQL repair using DB error feedback (ReAct).

When the connector raises an exception, we hand the error message back to the
LLM together with the original query and schema, and ask it to produce a
corrected SQL statement.
"""
from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from ..llm_client import LLMClient
from ..prompts.templates import SQL_FIX_SYSTEM_PROMPT, SQL_FIX_USER_PROMPT


class SQLVerifier:
    """Lightweight wrapper that fixes a failed SQL by consulting the LLM."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def fix(
        self,
        *,
        query: str,
        schema: List[Dict[str, Any]],
        previous_sql: str,
        error: str,
    ) -> str:
        """Return a corrected SQL string. Caller is responsible for safety checks."""
        system = SQL_FIX_SYSTEM_PROMPT
        user = SQL_FIX_USER_PROMPT.format(
            query=query,
            schema=schema,
            previous_sql=previous_sql,
            error=error,
        )
        try:
            fixed = self.llm.chat(user, system=system)
        except Exception as exc:  # pragma: no cover - LLM 不可用
            logger.warning(f"SQLVerifier.fix failed: {exc}")
            return previous_sql

        return _strip_sql(fixed)


def _strip_sql(raw: str) -> str:
    """Drop markdown fences, prose, and any trailing statements."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    for prefix in ("SQL:", "Sql:", "sql:", "Corrected SQL:", "Corrected:"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):].lstrip()
    raw = raw.split(";")[0].strip()
    return raw
