"""Schema index tests — covers keyword fallback, embedding search, and metadata filtering."""
from __future__ import annotations

import numpy as np

from askdata.connectors.base import BaseConnector
from askdata.metadata.schema_index import (
    GENERIC_COLUMN_BLACKLIST,
    RATE_QUERY_KEYWORDS,
    TIME_QUERY_KEYWORDS,
    SchemaIndex,
)


# ---------- Fakes ----------
class FakeConnector(BaseConnector):
    """In-memory connector — no DB needed."""

    name = "fake"

    def __init__(self, schema):
        self._schema = schema

    def execute_readonly(self, sql, params=None):
        return []

    def get_schema(self):
        return self._schema


class FakeEmbedding:
    """Deterministic fake embedding for tests.

    Maps each character to a dimension via hash, then L2-normalizes.
    Same/similar text -> similar vectors.
    """

    DIM = 1024

    def encode(self, texts, normalize_embeddings=True):
        if isinstance(texts, str):
            texts = [texts]
        vecs = np.zeros((len(texts), self.DIM), dtype=np.float32)
        for i, t in enumerate(texts):
            for ch in t.lower():
                idx = hash(ch) % self.DIM
                vecs[i, idx] += 1.0
        if normalize_embeddings:
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vecs = vecs / norms
        return vecs


# ---------- 关键字降级方案 ----------
def test_keyword_search_finds_matching_table():
    schema = [
        {"table_name": "orders", "column_name": "user_id", "data_type": "int"},
        {"table_name": "orders", "column_name": "amount", "data_type": "numeric"},
        {"table_name": "users", "column_name": "email", "data_type": "text"},
    ]
    idx = SchemaIndex(FakeConnector(schema), use_embeddings=False)
    hits = idx.search("orders by amount", top_k=5)
    assert hits
    assert hits[0]["table_name"] == "orders"


def test_keyword_search_returns_empty_for_unrelated_query():
    schema = [{"table_name": "orders", "column_name": "amount", "data_type": "numeric"}]
    idx = SchemaIndex(FakeConnector(schema), use_embeddings=False)
    # 用一个跟 amount 完全无关的中文 query,关键字打分应返回 0
    assert idx.search("天气预报", top_k=5) == []


# ---------- Embedding 检索 ----------
def test_embedding_search_finds_relevant_field():
    schema = [
        {"table_name": "orders", "column_name": "amount", "data_type": "numeric"},
        {"table_name": "orders", "column_name": "user_id", "data_type": "int"},
        {"table_name": "products", "column_name": "price", "data_type": "numeric"},
    ]
    idx = SchemaIndex(
        connector=FakeConnector(schema),
        embedding_model=FakeEmbedding(),
        use_embeddings=True,
    )
    hits = idx.search("订单金额")
    assert hits
    # "金额"相关字段必须在结果里
    cols = [h["column_name"] for h in hits]
    assert "amount" in cols


def test_embedding_search_with_metadata_filter():
    schema = [
        {"table_name": "orders", "column_name": "amount", "data_type": "numeric"},
        {"table_name": "orders", "column_name": "user_id", "data_type": "int"},
        {"table_name": "products", "column_name": "id", "data_type": "int"},  # 黑名单
    ]
    idx = SchemaIndex(
        connector=FakeConnector(schema),
        embedding_model=FakeEmbedding(),
        use_embeddings=True,
    )
    hits = idx.search("复购率", top_k=5)
    # 黑名单字段 id 必须被过滤掉
    cols = [h["column_name"] for h in hits]
    assert "id" not in cols


# ---------- 元数据过滤 ----------
def test_rate_query_filters_irrelevant_fields():
    schema = [
        {"table_name": "orders", "column_name": "amount", "data_type": "numeric"},
        {"table_name": "orders", "column_name": "user_email", "data_type": "text"},
    ]
    idx = SchemaIndex(
        connector=FakeConnector(schema),
        embedding_model=FakeEmbedding(),
        use_embeddings=True,
    )
    hits = idx.search("复购率是多少", top_k=5)
    cols = [h["column_name"] for h in hits]
    # 复购率类问题应该优先保留 amount(命中 RATE_RELATED_COLUMN_KEYWORDS)
    assert "amount" in cols


def test_time_query_keeps_time_fields():
    schema = [
        {"table_name": "orders", "column_name": "created_at", "data_type": "timestamp"},
        {"table_name": "orders", "column_name": "amount", "data_type": "numeric"},
        {"table_name": "users", "column_name": "email", "data_type": "text"},  # users 不是订单/日志类表
    ]
    idx = SchemaIndex(
        connector=FakeConnector(schema),
        embedding_model=FakeEmbedding(),
        use_embeddings=True,
    )
    hits = idx.search("Q3 订单数", top_k=5)
    cols = [h["column_name"] for h in hits]
    # 时间字段 created_at 必须保留
    assert "created_at" in cols
    # users.email 表名不在 TIME_RELATED_TABLE_HINTS 中,非时间字段被过滤
    assert "email" not in cols


def test_generic_blacklist_always_filtered():
    for col in GENERIC_COLUMN_BLACKLIST:
        schema = [{"table_name": "orders", "column_name": col, "data_type": "timestamp"}]
        idx = SchemaIndex(
            connector=FakeConnector(schema),
            embedding_model=FakeEmbedding(),
            use_embeddings=True,
        )
        hits = idx.search("查一下订单信息", top_k=5)
        assert hits == [], f"blacklist field '{col}' should be filtered out"


# ---------- 调试接口 ----------
def test_debug_search_returns_scores():
    schema = [
        {"table_name": "orders", "column_name": "amount", "data_type": "numeric"},
        {"table_name": "orders", "column_name": "user_id", "data_type": "int"},
    ]
    idx = SchemaIndex(
        connector=FakeConnector(schema),
        embedding_model=FakeEmbedding(),
        use_embeddings=True,
    )
    debug = idx.debug_search("订单金额", top_k=2)
    assert all("score" in d and "passed_filter" in d for d in debug)


# ---------- 注释生成缓存 ----------
def test_field_descriptions_loaded_from_cache(tmp_path):
    """验证 refresh 时会读已有缓存的注释(不需要 LLM)。"""
    cache_file = tmp_path / "descriptions.yaml"
    cache_file.write_text(
        "fields:\n"
        "  orders.amount: 订单金额,单位元\n"
        "  orders.user_id: 下单用户 ID\n",
        encoding="utf-8",
    )
    schema = [
        {"table_name": "orders", "column_name": "amount", "data_type": "numeric"},
        {"table_name": "orders", "column_name": "user_id", "data_type": "int"},
    ]
    # llm=None 时只读缓存,不生成
    idx = SchemaIndex(
        connector=FakeConnector(schema),
        embedding_model=FakeEmbedding(),
        llm=None,
        descriptions_cache=str(cache_file),
        use_embeddings=True,
    )
    assert idx.descriptions["orders.amount"] == "订单金额,单位元"
    # _docs 应该把注释拼进去
    assert any("订单金额" in doc for doc in idx._docs)
