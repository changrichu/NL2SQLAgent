"""NL2SQL Agent — orchestrator with ReAct-style self-correction.

Pipeline (each step is logged for traceability):

    1. SchemaIndex.search    -> relevant columns (BGE-M3 + metadata filter)
    2. MetricsRegistry.search -> relevant business metrics
    3. LLM                   -> initial SQL
    4. SQLSafety             -> keyword whitelist + dangerous-pattern regex
    5. connector             -> execute SQL; on failure go to (6)
    6. SQLVerifier           -> ask LLM to fix SQL using DB error message
       loop back to (4), up to MAX_RETRIES times
    7. chart_recommender     -> pick chart type from result shape
    8. LLM                   -> 1-2 sentence Chinese insight

Returns a dict suitable for both REST API and Streamlit UI.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

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
from ..tools import recommend_chart
from .verifier import SQLVerifier, _strip_sql as _verifier_strip_sql


# 最多自检 2 次(原始 1 次 + 修复 2 次 = 3 次机会)
DEFAULT_MAX_RETRIES = 2


class NL2SQLAgent:
    """End-to-end Text-to-SQL pipeline for a single data source."""

    def __init__(
        self,
        llm: LLMClient,
        datasource: str = "postgres",
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        if datasource not in CONNECTOR_REGISTRY:
            raise ValueError(f"Unknown datasource: {datasource}")
        self.llm = llm
        self.datasource = datasource
        self.max_retries = max_retries
        connector_cls = CONNECTOR_REGISTRY[datasource]()
        self.connector = connector_cls()
        self.schema_index = SchemaIndex(self.connector)
        self.metrics = MetricsRegistry()
        self.verifier = SQLVerifier(llm)

    # =========================================================
    # Public API
    # =========================================================
    def run(self, query: str, user_id: str = "anonymous") -> Dict[str, Any]:
        logger.info(f"📊 NL2SQL | datasource={self.datasource} query={query!r} user={user_id}")

        relevant_tables = self.schema_index.search(query, top_k=5)
        relevant_metrics = self.metrics.search(query)

        # 第 1 次生成 SQL
        sql = self._generate_sql(query, relevant_tables, relevant_metrics)

        # ReAct 循环:出错就改写
        sql, results, error = self._execute_with_retry(
            query=query, schema=relevant_tables, initial_sql=sql
        )

        if error:
            return error

        # 成功 → 格式化 + 自动图表 + 中文摘要
        return self._format_response(query=query, sql=sql, results=results)

    # =========================================================
    # SQL 生成
    # =========================================================
    def _generate_sql(
        self,
        query: str,
        schema: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
    ) -> str:
        system_prompt = NL2SQL_SYSTEM_PROMPT.format(
            schema=schema, metrics=metrics,
        )
        raw = self.llm.chat(
            prompt=NL2SQL_USER_PROMPT.format(query=query),
            system=system_prompt,
        )
        return self._strip_sql(raw)

    # =========================================================
    # ReAct 自检循环
    # =========================================================
    def _execute_with_retry(
        self,
        *,
        query: str,
        schema: List[Dict[str, Any]],
        initial_sql: str,
    ) -> tuple[str, Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """Returns (sql, results | None, error_dict | None)."""

        sql = initial_sql
        for attempt in range(self.max_retries + 1):
            # 安全 guard
            sql_with_limit = SQLSafety.add_limit(sql)
            if not SQLSafety.is_safe(sql_with_limit):
                logger.error(f"Unsafe SQL blocked: {sql_with_limit}")
                return sql, None, {
                    "error": "❌ Generated SQL was unsafe and was blocked.",
                    "sql": sql_with_limit,
                }

            # 执行
            try:
                results = self.connector.execute_readonly(sql_with_limit)
                logger.info(f"✅ SQL succeeded on attempt {attempt + 1}, {len(results)} rows")
                return sql_with_limit, results, None
            except Exception as exc:
                logger.warning(f"⚠️ SQL failed on attempt {attempt + 1}: {exc}")
                if attempt >= self.max_retries:
                    # 用完所有机会
                    return sql_with_limit, None, {
                        "error": f"❌ Execution failed after {attempt + 1} attempts: {exc}",
                        "sql": sql_with_limit,
                    }

                # ReAct:让 LLM 看错误信息,改写 SQL
                fixed = self.verifier.fix(
                    query=query,
                    schema=schema,
                    previous_sql=sql_with_limit,
                    error=str(exc),
                )
                sql = self._strip_sql(fixed)

        # 理论上到不了这里
        return sql, None, {"error": "❌ Unknown failure", "sql": sql}

    # =========================================================
    # 结果格式化 + 自动摘要
    # =========================================================
    def _format_response(
        self, *, query: str, sql: str, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        normalized = _normalize_results(results)
        chart = recommend_chart(normalized)
        explanation = self._explain(query=query, sql=sql, results=normalized)

        return {
            "sql": sql,
            "results": normalized,
            "row_count": len(normalized),
            "chart": chart,
            "explanation": explanation,
        }

    def _explain(self, *, query: str, sql: str, results: List[Dict[str, Any]]) -> str:
        sample = results[:5]
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

    # =========================================================
    # 辅助
    # =========================================================
    @staticmethod
    def _strip_sql(raw: str) -> str:
        return _verifier_strip_sql(raw)


# ---------- 结果类型归一化 ----------
def _normalize_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 datetime/Decimal 转成 JSON 友好的类型。"""
    out: List[Dict[str, Any]] = []
    for row in results:
        normalized = {}
        for k, v in row.items():
            if isinstance(v, datetime):
                normalized[k] = v.isoformat()
            elif isinstance(v, date):
                normalized[k] = v.isoformat()
            elif isinstance(v, Decimal):
                normalized[k] = float(v)
            else:
                normalized[k] = v
        out.append(normalized)
    return out
