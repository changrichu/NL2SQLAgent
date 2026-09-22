"""Schema index — BGE-M3 Embedding + 元数据过滤。

两阶段检索:
  1. 入库阶段 (refresh):
     - 从 information_schema 拉所有字段
     - 用 LLM 给每个字段生成中文描述(缓存到 YAML)
     - 把"表 X 的 Y 字段,类型 Z,含义:..." 编码成 1024 维向量
     - 向量缓存在内存中

  2. 查询阶段 (search):
     - 用户问题 → Embedding → 1024 维向量
     - 与所有字段向量算 cosine 相似度 → top 20 候选
     - 元数据过滤(率类/时间类/通用黑名单) → top K

无 embedding_model 时降级为关键字打分,保证不依赖 GPU 也能跑通。
"""
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from ..connectors.base import BaseConnector
from .field_descriptions import FieldDescriptionGenerator


# ---------- 元数据过滤规则 ----------
# 太过通用、单独召回没意义的字段(在所有查询里都会出现噪音)
GENERIC_COLUMN_BLACKLIST: Set[str] = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "modified_at",
    "create_time",
    "update_time",
}

# "率/占比/同比/环比"类问题需要保留的字段关键字(英文列名命中这些词才算相关)
RATE_RELATED_COLUMN_KEYWORDS: Set[str] = {
    "count", "rate", "percent", "amount", "total", "sum", "avg",
    "quantity", "qty", "score", "num",
}

# 时间类问题需要保留的时间字段类型
TIME_FIELD_TYPES: Set[str] = {
    "timestamp", "timestamptz", "date", "datetime",
    "time", "datetime2",
}

# 时间类问题中,非时间字段要保留的"上下文关键字"
TIME_RELATED_TABLE_HINTS: Set[str] = {
    "order", "log", "record", "event", "trade", "transaction", "payment", "visit",
}

# 触发"率类过滤"的查询关键字
RATE_QUERY_KEYWORDS: Set[str] = {"率", "占比", "百分比", "同比", "环比", "percent", "rate"}

# 触发"时间类过滤"的查询关键字
TIME_QUERY_KEYWORDS: Set[str] = {
    "Q1", "Q2", "Q3", "Q4",
    "今天", "昨天", "最近", "上月", "上个月", "本周", "上周", "本季度", "上季度", "本年", "去年",
    "月", "年", "日", "天", "周", "季度",
}


class SchemaIndex:
    """Embedding + 元数据过滤的 schema 检索器。"""

    def __init__(
        self,
        connector: BaseConnector,
        embedding_model: Any = None,
        llm: Any = None,
        descriptions_cache: str = "config/field_descriptions.yaml",
        use_embeddings: bool = False,
    ):
        """
        Args:
            connector: 数据源连接器,提供 get_schema()
            embedding_model: SentenceTransformer 实例(可选)
            llm: LLMClient 实例(可选,用于自动生成字段注释)
            descriptions_cache: 字段注释 YAML 缓存路径
            use_embeddings: 是否使用向量检索;False 时降级为关键字打分
        """
        self.connector = connector
        self.embedding_model = embedding_model
        self.llm = llm
        self.descriptions_cache_path = descriptions_cache
        self.use_embeddings = use_embeddings and embedding_model is not None

        self._schema: List[Dict[str, Any]] = []
        self._docs: List[str] = []
        self._vectors: Optional[np.ndarray] = None
        self._descriptions: Dict[str, str] = {}

        self.refresh()

    # ==================== 入库阶段 ====================
    def refresh(self) -> None:
        """重新拉 Schema + 生成注释 + 重新编码向量。"""
        self._schema = self.connector.get_schema()

        # 字段注释(LLM 生成 + YAML 缓存)
        gen = FieldDescriptionGenerator(self.llm, self.descriptions_cache_path)
        self._descriptions = gen.generate_for_schema(self._schema)

        # 拼自然语言描述
        self._docs = [self._format_doc(row) for row in self._schema]

        # 向量编码
        if self.use_embeddings and self.embedding_model is not None:
            try:
                self._vectors = self.embedding_model.encode(
                    self._docs, normalize_embeddings=True
                )
            except Exception:  # pragma: no cover - 模型失败兜底
                self._vectors = None
                self.use_embeddings = False

    def _format_doc(self, row: Dict[str, Any]) -> str:
        key = f"{row['table_name']}.{row['column_name']}"
        desc = self._descriptions.get(key, "")
        base = (
            f"表 {row['table_name']} 的 {row['column_name']} 字段,"
            f"类型 {row['data_type']}"
        )
        if desc:
            base += f",含义:{desc}"
        return base

    # ==================== 查询阶段 ====================
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索与 query 相关的字段列表。"""
        if not self._schema:
            return []

        if self.use_embeddings and self._vectors is not None:
            return self._search_by_embedding(query, top_k)
        return self._search_by_keyword(query, top_k)

    def _search_by_embedding(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        assert self.embedding_model is not None
        assert self._vectors is not None

        q_vec = self.embedding_model.encode([query], normalize_embeddings=True)
        scores = (self._vectors @ q_vec.T).flatten()

        # 放宽召回:取 top 20 候选,再过滤
        candidate_n = min(20, len(self._schema))
        candidate_idx = np.argsort(scores)[::-1][:candidate_n]
        candidates: List[Tuple[float, Dict[str, Any]]] = [
            (float(scores[i]), self._schema[i]) for i in candidate_idx
        ]

        filtered = [
            (s, row) for s, row in candidates
            if self._passes_metadata_filter(query, row)
        ]
        return [row for _, row in filtered[:top_k]]

    def _search_by_keyword(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """降级方案:纯关键字打分,字段描述进文本。"""
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for row in self._schema:
            key = f"{row['table_name']}.{row['column_name']}"
            text = (
                f"{row['table_name']} {row['column_name']} "
                f"{row['data_type']} {self._descriptions.get(key, '')}"
            )
            s = self._keyword_score(query, text)
            if s > 0:
                scored.append((s, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    @staticmethod
    def _keyword_score(query: str, text: str) -> int:
        score = 0
        text_lower = text.lower()
        for token in query.lower().split():
            if token and token in text_lower:
                score += 1
        return score

    # ==================== 元数据过滤 ====================
    def _passes_metadata_filter(self, query: str, row: Dict[str, Any]) -> bool:
        col_lower = row["column_name"].lower()
        dtype = row["data_type"].lower()
        table_lower = row["table_name"].lower()
        is_time_field = dtype in TIME_FIELD_TYPES

        # 优先级 1:时间字段在时间类问题中永远保留(包括 created_at 等黑名字段)
        if is_time_field and any(k in query for k in TIME_QUERY_KEYWORDS):
            return True

        # 通用黑名单(非时间上下文中)
        if col_lower in GENERIC_COLUMN_BLACKLIST:
            return False

        # 约束 1:率类问题 → 字段名必须沾边
        if any(k in query for k in RATE_QUERY_KEYWORDS):
            if not any(w in col_lower for w in RATE_RELATED_COLUMN_KEYWORDS):
                return False

        # 约束 2:时间类问题
        if any(k in query for k in TIME_QUERY_KEYWORDS):
            # 非时间字段:要求表名是订单/日志/记录类业务表
            if not any(w in table_lower for w in TIME_RELATED_TABLE_HINTS):
                return False

        return True

    # ==================== 调试辅助 ====================
    @property
    def schema(self) -> List[Dict[str, Any]]:
        return self._schema

    @property
    def descriptions(self) -> Dict[str, str]:
        return self._descriptions

    def debug_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """带分数和过滤原因的检索,用于调试。"""
        if not self.use_embeddings or self._vectors is None:
            return [{"row": r, "score": 0.0} for r in self.search(query, top_k)]

        q_vec = self.embedding_model.encode([query], normalize_embeddings=True)
        scores = (self._vectors @ q_vec.T).flatten()
        candidate_n = min(20, len(self._schema))
        candidate_idx = np.argsort(scores)[::-1][:candidate_n]

        results = []
        for i in candidate_idx:
            row = self._schema[i]
            passed = self._passes_metadata_filter(query, row)
            results.append({
                "row": row,
                "score": float(scores[i]),
                "passed_filter": passed,
            })
            if len([r for r in results if r["passed_filter"]]) >= top_k:
                break
        return results
