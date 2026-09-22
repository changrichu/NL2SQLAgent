"""Tests for the NL2SQL agent — ReAct self-correction loop, result formatting, normalization.

We mock the LLM so tests are deterministic and free.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from askdata.agent.nl2sql_agent import NL2SQLAgent, _normalize_results
from askdata.connectors.base import BaseConnector
from askdata.llm_client import LLMClient


# ---------- Fakes ----------
class FakeLLM(LLMClient):
    """Sequence-driven fake — chat() returns the next preset response."""

    def __init__(self, responses: List[str]):
        # skip real init
        self._responses = list(responses)
        self._call_log: List[Dict[str, Any]] = []

    def chat(self, prompt: str, system: Optional[str] = None, temperature: float = 0.1) -> str:
        self._call_log.append({"prompt": prompt, "system": system})
        if not self._responses:
            return ""
        return self._responses.pop(0)


class FlakyConnector(BaseConnector):
    """Fails the first N execute_readonly calls, then succeeds."""

    name = "flaky"

    def __init__(self, schema, results: List[Dict[str, Any]], fail_count: int = 1):
        self._schema = schema
        self._results = results
        self._fail_count = fail_count
        self.attempts = 0

    def execute_readonly(self, sql, params=None):
        self.attempts += 1
        if self.attempts <= self._fail_count:
            raise RuntimeError(f"column orders.amoun does not exist (attempt {self.attempts})")
        return self._results

    def get_schema(self):
        return self._schema


# ---------- 归一化 ----------
def test_normalize_decimal_to_float():
    from decimal import Decimal
    out = _normalize_results([{"amount": Decimal("99.50")}])
    assert out[0]["amount"] == 99.5
    assert isinstance(out[0]["amount"], float)


def test_normalize_datetime_to_iso():
    from datetime import datetime
    dt = datetime(2026, 9, 23, 10, 30, 0)
    out = _normalize_results([{"ts": dt}])
    assert out[0]["ts"] == "2026-09-23T10:30:00"


def test_normalize_passes_through_primitives():
    out = _normalize_results([{"a": 1, "b": "x", "c": True, "d": None}])
    assert out[0] == {"a": 1, "b": "x", "c": True, "d": None}


# ---------- 一次性成功 ----------
def test_run_succeeds_on_first_attempt():
    schema = [{"table_name": "orders", "column_name": "amount", "data_type": "numeric"}]
    connector = FlakyConnector(schema, [{"amount": 100}], fail_count=0)
    llm = FakeLLM(["SELECT amount FROM orders"])
    agent = NL2SQLAgent.__new__(NL2SQLAgent)
    agent.llm = llm
    agent.datasource = "flaky"
    agent.max_retries = 2
    agent.connector = connector
    agent.schema_index = None  # type: ignore
    agent.metrics = None  # type: ignore
    agent.verifier = None  # type: ignore

    # 调用一个简化版 helper,绕过 schema_index
    sql = agent._strip_sql(llm.chat(""))
    sql_with_limit = sql  # safety 已在 connector 内,这里不测
    # 直接验证 _execute_with_retry 的成功路径
    final_sql, results, error = agent._execute_with_retry(
        query="?", schema=schema, initial_sql=sql,
    )
    assert error is None
    assert results == [{"amount": 100}]
    assert connector.attempts == 1


# ---------- ReAct:第一次失败,第二次成功 ----------
def test_run_retries_on_failure_then_succeeds():
    schema = [{"table_name": "orders", "column_name": "amount", "data_type": "numeric"}]
    connector = FlakyConnector(schema, [{"amount": 100}], fail_count=1)
    llm_responses = [
        "SELECT amoun FROM orders",       # 第 1 次生成(有错)
        "SELECT amount FROM orders",      # verifier 改写后(成功)
        "查询返回 1 行,金额为 100。",        # 摘要
    ]
    llm = FakeLLM(llm_responses)
    agent = NL2SQLAgent.__new__(NL2SQLAgent)
    agent.llm = llm
    agent.datasource = "flaky"
    agent.max_retries = 2
    agent.connector = connector
    agent.schema_index = None  # type: ignore
    agent.metrics = None  # type: ignore
    agent.verifier = type("V", (), {"fix": staticmethod(
        lambda **kw: llm_responses[1] if "amoun" in kw["previous_sql"] else kw["previous_sql"]
    )})()

    final_sql, results, error = agent._execute_with_retry(
        query="查金额", schema=schema,
        initial_sql="SELECT amoun FROM orders",
    )
    assert error is None
    assert results == [{"amount": 100}]
    assert connector.attempts == 2  # 失败 1 次 + 成功 1 次


# ---------- ReAct:重试耗尽 ----------
def test_run_exhausts_retries():
    schema = [{"table_name": "orders", "column_name": "amount", "data_type": "numeric"}]
    connector = FlakyConnector(schema, [{"amount": 100}], fail_count=10)  # 一直失败
    llm = FakeLLM(["SELECT * FROM orders"] * 10)

    agent = NL2SQLAgent.__new__(NL2SQLAgent)
    agent.llm = llm
    agent.datasource = "flaky"
    agent.max_retries = 2
    agent.connector = connector
    agent.schema_index = None  # type: ignore
    agent.metrics = None  # type: ignore

    class FailingVerifier:
        def fix(self, **kw):
            # verifier 永远返回同样错的 SQL(模拟改不动)
            return "SELECT * FROM nonexistent"

    agent.verifier = FailingVerifier()

    final_sql, results, error = agent._execute_with_retry(
        query="?", schema=schema,
        initial_sql="SELECT * FROM orders",
    )
    assert results is None
    assert error is not None
    assert "Execution failed" in error["error"]
    assert connector.attempts == 3  # 1 初始 + 2 retries


# ---------- 结果格式化 ----------
def test_format_response_includes_chart_and_explanation():
    agent = NL2SQLAgent.__new__(NL2SQLAgent)
    agent.llm = FakeLLM(["查询返回 1 行,金额为 100。"])
    out = agent._format_response(
        query="查金额",
        sql="SELECT amount FROM orders",
        results=[{"amount": 100}],
    )
    assert "sql" in out and "results" in out
    assert "chart" in out
    assert out["chart"]["chart_type"] == "kpi_card"
    assert "explanation" in out
    assert out["row_count"] == 1
