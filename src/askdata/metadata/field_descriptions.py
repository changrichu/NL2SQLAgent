"""字段注释生成器 — 用 LLM 自动给每个字段生成中文描述,缓存到 YAML。

为什么要这个?
- 数据库 information_schema 只有字段名和类型,没有"业务含义"
- BGE-M3 Embedding 需要把字段编成自然语言句,光给字段名语义太弱
- 一次性 LLM 生成,后续读 YAML 缓存,产品经理还能手动校对

典型用法:
    >>> gen = FieldDescriptionGenerator(llm_client)
    >>> descriptions = gen.generate_for_schema(schema_rows)
    >>> desc = gen.get("orders", "amount")  # -> "订单金额,单位元"
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..llm_client import LLMClient


GENERATE_DESCRIPTION_PROMPT = """你是数据库文档助手。请根据数据库表的字段名和数据类型,
用一句中文(10-25 字)描述这个字段的业务含义。

要求:
- 简洁,不要技术术语
- 业务语言,产品经理能看懂
- 如果字段名是英文且无法判断含义,根据常见命名约定(orders=订单、users=用户、amount=金额)合理推断
- 直接输出描述,不要前缀(如"该字段表示"),不要引号

字段名:{table_name}.{column_name}
数据类型:{data_type}

描述:"""


class FieldDescriptionGenerator:
    """LLM 驱动的字段注释生成器,带 YAML 缓存。"""

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        cache_path: str = "config/field_descriptions.yaml",
    ):
        # llm 可为 None,表示只读已有缓存,不再生成
        self.llm = llm
        self.cache_path = Path(cache_path)
        self._cache: Dict[str, str] = self._load_cache()

    # ---------- 缓存读写 ----------
    def _load_cache(self) -> Dict[str, str]:
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return {}
        return data.get("fields", {})

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                {"fields": self._cache},
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

    @staticmethod
    def _make_key(table: str, column: str) -> str:
        return f"{table}.{column}"

    # ---------- 核心 ----------
    def get(self, table: str, column: str) -> str:
        return self._cache.get(self._make_key(table, column), "")

    def generate_for_schema(
        self,
        schema: List[Dict[str, Any]],
        force: bool = False,
        on_progress: Optional[Any] = None,
    ) -> Dict[str, str]:
        """遍历 schema,对缺失字段调用 LLM 生成中文描述。

        Args:
            schema: connector.get_schema() 返回的字段列表
            force: True 时强制重新生成所有字段(覆盖缓存)
            on_progress: 可选回调 (done, total, key) 用于进度显示
        """
        if not self.llm:
            # 没有 LLM 就只返回缓存
            return self._cache

        to_generate: List[tuple] = []
        for row in schema:
            key = self._make_key(row["table_name"], row["column_name"])
            if force or key not in self._cache or not self._cache[key]:
                to_generate.append((key, row))

        if not to_generate:
            return self._cache

        total = len(to_generate)
        for idx, (key, row) in enumerate(to_generate, 1):
            prompt = GENERATE_DESCRIPTION_PROMPT.format(
                table_name=row["table_name"],
                column_name=row["column_name"],
                data_type=row["data_type"],
            )
            try:
                desc = self.llm.chat(prompt).strip().strip("。").strip(".").strip()
                # 去掉可能的前缀(如"该字段表示"、"含义:")
                for prefix in ["该字段表示", "该字段", "表示", "含义:", "描述:"]:
                    if desc.startswith(prefix):
                        desc = desc[len(prefix):].strip()
                if not desc:
                    raise ValueError("empty description")
                self._cache[key] = desc
            except Exception as exc:  # pragma: no cover - LLM 调用失败兜底
                # 兜底:不阻塞主流程,留个能用的占位描述
                self._cache[key] = f"{row['column_name']}({row['data_type']})"

            if on_progress:
                on_progress(idx, total, key)

        self._save_cache()
        return self._cache
