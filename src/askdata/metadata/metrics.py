"""Business metrics registry — single source of truth for shared KPIs.

Define metrics in `config/metrics.yaml` so product/ops folks can edit them
without touching code. The agent uses this to translate fuzzy terms like
"复购率" into a deterministic SQL template.
"""
from pathlib import Path
from typing import Any, Dict, List

import yaml


class MetricsRegistry:
    def __init__(self, config_path: str = "config/metrics.yaml"):
        self.config_path = config_path
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        path = Path(self.config_path)
        if not path.exists():
            self.metrics = {}
            return
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.metrics = data.get("metrics", {})

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        results: List[Dict[str, Any]] = []
        for name, defn in self.metrics.items():
            haystack = f"{name} {defn.get('description', '')}".lower()
            if q in haystack:
                results.append({"name": name, **defn})
        return results

    def get_sql_template(self, metric_name: str) -> str:
        return self.metrics.get(metric_name, {}).get("sql_template", "")
