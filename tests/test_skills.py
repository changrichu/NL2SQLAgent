"""Tests for the industry skill registry."""
from __future__ import annotations

from pathlib import Path

import pytest

from askdata.skills.registry import SkillRegistry


# ---------- 内置 skill 加载 ----------
def test_default_registry_finds_three_skills():
    reg = SkillRegistry()
    skills = reg.skills
    assert "ecommerce" in skills
    assert "saas" in skills
    assert "education" in skills


def test_ecommerce_has_at_least_15_metrics():
    reg = SkillRegistry()
    metrics = reg.get_metrics("ecommerce")
    assert len(metrics) >= 15
    # 关键指标必须存在
    for required in ["GMV", "复购率", "客单价", "退款率_30天", "热销商品TOP10"]:
        assert required in metrics


def test_saas_has_core_saas_metrics():
    reg = SkillRegistry()
    metrics = reg.get_metrics("saas")
    for required in ["MAU", "DAU", "MRR", "Churn率_月", "LTV", "NPS"]:
        assert required in metrics


def test_education_has_core_education_metrics():
    reg = SkillRegistry()
    metrics = reg.get_metrics("education")
    for required in ["完课率", "续报率", "退课率_90天", "NPS"]:
        assert required in metrics


def test_list_skills_returns_metadata():
    reg = SkillRegistry()
    listing = reg.list_skills()
    assert isinstance(listing, list)
    for entry in listing:
        assert "name" in entry
        assert "description" in entry
        assert "metric_count" in entry
        assert "metrics" in entry
        assert entry["metric_count"] == len(entry["metrics"])


# ---------- 自定义 skill 目录 ----------
def test_custom_skills_root(tmp_path):
    """支持从任意目录加载(便于以后做多租户/插件化)。"""
    skill_dir = tmp_path / "finance"
    skill_dir.mkdir()
    (skill_dir / "metrics.yaml").write_text(
        "skill: finance\n"
        "description: 财务指标\n"
        "metrics:\n"
        "  月营收:\n"
        "    description: 当月营收\n"
        "    sql_template: SELECT 1\n",
        encoding="utf-8",
    )
    reg = SkillRegistry(skills_root=tmp_path)
    assert "finance" in reg.skills
    assert reg.get_metrics("finance")["月营收"]["sql_template"] == "SELECT 1"


def test_unknown_skill_raises():
    reg = SkillRegistry()
    with pytest.raises(KeyError):
        reg.get_skill("nonexistent")


# ---------- apply 到 MetricsRegistry ----------
def test_apply_to_metrics_registry():
    """把 skill 的指标合并进 MetricsRegistry,覆盖已有同名项。"""
    from askdata.metadata.metrics import MetricsRegistry

    reg = SkillRegistry()
    metrics = MetricsRegistry(config_path="/tmp/_unused_for_test.yaml")
    metrics.metrics = {
        "GMV": {"description": "用户自定义的 GMV", "sql_template": "SELECT 999"},
        "自定义指标": {"description": "测试", "sql_template": "SELECT 1"},
    }

    added = reg.apply_to_metrics_registry("ecommerce", metrics)

    # 用户的"自定义指标"保留
    assert "自定义指标" in metrics.metrics
    # skill 的指标全部注入
    ecommerce_metrics = reg.get_metrics("ecommerce")
    for name in ecommerce_metrics:
        assert name in metrics.metrics
    # skill 同名覆盖用户的
    assert metrics.metrics["GMV"]["sql_template"] == ecommerce_metrics["GMV"]["sql_template"]
    assert added == len(ecommerce_metrics)


def test_describe_format():
    reg = SkillRegistry()
    desc = reg.describe("ecommerce")
    assert "ecommerce" in desc
    assert "GMV" in desc
