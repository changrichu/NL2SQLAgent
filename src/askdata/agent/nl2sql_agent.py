"""NL2SQL Agent — orchestrates schema lookup, metric retrieval, SQL generation, safety check, execution, and result explanation."""
from typing import Any, Dict

from loguru import logger

from ..connectors import CONNECTOR_REGISTRY
from ..llm_client import LLMClient
from ..metadata.metrics import MetricsRegistry
from ..metadata.schema_index import SchemaIndex
from ..prompts.templates import (
    EXPLAIN_SYSTEM_PROMPT,
    EXPLAIN_USER_PROMPT,
    NL2SQL_SYSTEM_PROMPT,
    NL2SQL_USER_PROMPT,
)
from ..sql.safety import SQLSafety


class NL2SQLAgent:
    """End-to-end Text-to-SQL pipeline for a single data source."""

    def __init__(self, llm: LLMClient, datasource: str = "postgres"):
        if datasource not in CONNECTOR_REGISTRY:
            raise ValueError(f"Unknown datasource: {datasource}")
        self.llm = llm
        self.datasource = datasource
        connector_cls = CONNECTOR_REGISTRY[datasource]()
        self.connector = connector_cls()
        self.schema_index = SchemaIndex(self.connector)
        self.metrics = MetricsRegistry()

    def run(self, query: str, user_id: str = "anonymous") -> Dict[str, Any]:
        logger.info(f"📊 NL2SQL | datasource={self.datasource} query='{query}' user={user_id}")

        # 1. Pull relevant tables from schema index
        relevant_tables = self.schema_index.search(query, top_k=5)

        # 2. Pull matching business metrics
        relevant_metrics = self.metrics.search(query)

        # 3. Generate SQL
        system_prompt = NL2SQL_SYSTEM_PROMPT.format(
            schema=relevant_tables,
            metrics=relevant_metrics,
        )
        sql = self.llm.chat(
            prompt=NL2SQL_USER_PROMPT.format(query=query),
            system=system_prompt,
        )
        sql = _strip_sql(sql)
        logger.debug(f"Generated SQL: {sql}")

        # 4. Safety guard
        sql_with_limit = SQLSafety.add_limit(sql)
        if not SQLSafety.is_safe(sql_with_limit):
            logger.error(f"Unsafe SQL blocked: {sql_with_limit}")
            return {"error": "❌ Generated SQL was unsafe and was blocked.", "sql": sql_with_limit}

        # 5. Execute
        try:
            results = self.connector.execute_readonly(sql_with_limit)
        except Exception as exc:  # pragma: no cover - network/DB specific
            logger.exception("SQL execution failed")
            return {"error": f"❌ Execution failed: {exc}", "sql": sql_with_limit}

        # 6. Explain in natural language
        explanation = self._explain(query=query, sql=sql_with_limit, results=results)

        return {
            "sql": sql_with_limit,
            "results": results,
            "row_count": len(results),
            "explanation": explanation,
        }

    def _explain(self, query: str, sql: str, results) -> str:
        sample = results[:3] if results else []
        try:
            return self.llm.chat(
                prompt=EXPLAIN_USER_PROMPT.format(
                    query=query, sql=sql, row_count=len(results), sample=sample
                ),
                system=EXPLAIN_SYSTEM_PROMPT,
                temperature=0.3,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Explanation failed: {exc}")
            return f"查询返回 {len(results)} 行。"


def _strip_sql(raw: str) -> str:
    """Strip markdown fences and stray prose around the SQL body."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        # drop first fence line and trailing fence
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    # if LLM added a leading "SQL:" prefix, drop it
    for prefix in ("SQL:", "Sql:", "sql:"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):].lstrip()
    # take only the first statement
    raw = raw.split(";")[0].strip()
    return raw
