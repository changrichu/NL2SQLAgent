"""Industry skill registry — load and apply pre-built metric templates.

Each skill is a directory under ``askdata_skills/`` containing a ``metrics.yaml``
file. The registry scans for them on init, exposes a listing API, and knows
how to merge a skill's metrics into a ``MetricsRegistry`` instance.

Adding a new skill is a zero-code operation:

    mkdir askdata_skills/<your_skill>
    # write metrics.yaml
    # (optional) write README.md
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def _default_skills_root() -> Path:
    """askdata_skills/ sits at the project root, two levels above this file."""
    # this file: src/askdata/skills/registry.py
    return Path(__file__).resolve().parents[3] / "askdata_skills"


class SkillRegistry:
    """Discover, list, and apply industry metric templates."""

    def __init__(self, skills_root: Optional[Path] = None):
        self.skills_root = Path(skills_root) if skills_root else _default_skills_root()
        self._skills: Dict[str, Dict[str, Any]] = {}
        self.refresh()

    def refresh(self) -> None:
        """Reload all skills from disk."""
        self._skills = {}
        if not self.skills_root.exists():
            return
        for entry in sorted(self.skills_root.iterdir()):
            if not entry.is_dir() or entry.name.startswith(("_", ".")):
                continue
            metrics_file = entry / "metrics.yaml"
            if not metrics_file.exists():
                continue
            try:
                with open(metrics_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception:
                continue
            self._skills[entry.name] = data

    @property
    def skills(self) -> List[str]:
        return sorted(self._skills.keys())

    def list_skills(self) -> List[Dict[str, Any]]:
        """Return lightweight metadata for every available skill."""
        return [
            {
                "name": name,
                "description": data.get("description", ""),
                "metric_count": len(data.get("metrics", {})),
                "metrics": list(data.get("metrics", {}).keys()),
            }
            for name, data in sorted(self._skills.items())
        ]

    def get_skill(self, name: str) -> Dict[str, Any]:
        if name not in self._skills:
            raise KeyError(f"Unknown skill: {name!r}. Available: {self.skills}")
        return self._skills[name]

    def get_metrics(self, name: str) -> Dict[str, Dict[str, Any]]:
        return self.get_skill(name).get("metrics", {})

    def apply_to_metrics_registry(self, skill_name: str, metrics_registry: Any) -> int:
        """Merge a skill's metrics into a MetricsRegistry.

        Skill metrics override user-defined ones (skill = source of truth).

        Args:
            skill_name: e.g. "ecommerce"
            metrics_registry: an askdata.metadata.metrics.MetricsRegistry instance

        Returns:
            Number of metrics added/overridden.
        """
        skill_metrics = self.get_metrics(skill_name)
        if not skill_metrics:
            return 0
        metrics_registry.metrics.update(skill_metrics)
        return len(skill_metrics)

    def describe(self, name: str) -> str:
        """Human-readable summary of a skill for CLI / UI."""
        skill = self.get_skill(name)
        lines = [
            f"[{name}] {skill.get('description', '')}",
            f"  metrics: {len(skill.get('metrics', {}))}",
        ]
        for m in skill.get("metrics", {}).keys():
            lines.append(f"  - {m}")
        return "\n".join(lines)
