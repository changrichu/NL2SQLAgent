"""自动图表推荐 — 根据 SQL 结果的数据特征,推荐最合适的可视化形式。

启发式规则,无 LLM 依赖,毫秒级响应。

推荐类型:
  - line     折线图:有时间字段 + 数值字段(看趋势)
  - bar      柱状图:1 个分类 + 1 个数值(看对比)
  - pie      饼图:1 个分类 + 1 个数值,且 <= 8 行(看占比)
  - scatter  散点图:2 个数值字段(看相关)
  - kpi_card 数字卡:只有 1 列且全是数字(单一指标)
  - table    表格:列太多 / 类型不匹配
  - empty    空状态:无数据
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List


# 时间字符串格式(常见于 SQL 结果中的 ISO date / 'YYYY-MM' / 'YYYY-MM-DD HH:MM:SS')
TIME_STRING_PATTERNS = (
    re.compile(r"^\d{4}-\d{1,2}$"),                       # 2026-01
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"),              # 2026-01-15
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}[ T]\d{1,2}"),     # 2026-01-15 10 / 2026-01-15T10
    re.compile(r"^\d{4}/Q[1-4]$"),                        # 2026/Q1
    re.compile(r"^\d{4}Q[1-4]$"),                        # 2026Q1
    re.compile(r"^\d{4}年\d{1,2}月$"),                    # 2026年01月
)

TIME_FIELD_KEYWORDS = (
    "date", "time", "month", "day", "year", "quarter",
    "created", "updated", "at",
)


def _is_number(v: Any) -> bool:
    if v is None:
        return False
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)


def _is_time(v: Any) -> bool:
    if isinstance(v, (datetime, date)):
        return True
    if isinstance(v, str):
        s = v.strip()
        return any(p.match(s) for p in TIME_STRING_PATTERNS)
    return False


def _column_kind(rows: List[Dict[str, Any]], col: str) -> str:
    """判断一列的整体类型:number / time / category / mixed。"""
    non_null = [r[col] for r in rows if r.get(col) is not None]
    if not non_null:
        return "empty"
    n_num = sum(1 for v in non_null if _is_number(v))
    n_time = sum(1 for v in non_null if _is_time(v))
    n = len(non_null)
    if n_time / n >= 0.8:
        return "time"
    if n_num / n >= 0.8:
        return "number"
    return "category"


def recommend_chart(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """根据结果返回 {chart_type, x, y, reason}。"""
    if not results:
        return {"chart_type": "empty", "x": None, "y": None, "reason": "no data"}

    cols = list(results[0].keys())
    n_cols = len(cols)

    # 1 列 → KPI 数字卡
    if n_cols == 1:
        col = cols[0]
        kind = _column_kind(results, col)
        if kind == "number":
            return {
                "chart_type": "kpi_card",
                "x": col, "y": col,
                "reason": f"single numeric column {col!r}",
            }
        return {"chart_type": "kpi_card", "x": col, "y": None,
                "reason": f"single column {col!r}"}

    kinds = [_column_kind(results, c) for c in cols]

    # 2 列 → 多种可能(优先级:time > pie > bar > scatter)
    if n_cols == 2:
        c1, c2 = cols
        k1, k2 = kinds

        # 优先级 1:time + number → 折线(趋势 > 占比)
        if k1 == "time" and k2 == "number":
            return {"chart_type": "line", "x": c1, "y": c2,
                    "reason": "time series"}
        # 优先级 2:number + number → 散点
        if k1 == "number" and k2 == "number":
            return {"chart_type": "scatter", "x": c1, "y": c2,
                    "reason": "two numeric columns"}
        # 优先级 3:category + number + 行数小 → 饼图
        if k1 == "category" and k2 == "number" and len(results) <= 8:
            return {"chart_type": "pie", "x": c1, "y": c2,
                    "reason": "small category breakdown"}
        # 优先级 4:category + number → 柱状
        if k1 == "category" and k2 == "number":
            return {"chart_type": "bar", "x": c1, "y": c2,
                    "reason": "category vs metric"}
        # 其他
        return {"chart_type": "bar", "x": c1, "y": c2,
                "reason": "fallback two-column"}

    # 3 列 + 含 time → 多线
    if n_cols >= 3 and kinds[0] == "time" and "number" in kinds:
        num_col = next(c for c, k in zip(cols, kinds) if k == "number")
        return {"chart_type": "line", "x": cols[0], "y": num_col,
                "reason": "time + multiple series"}

    return {"chart_type": "table", "x": None, "y": None,
            "reason": f"{n_cols} columns"}
