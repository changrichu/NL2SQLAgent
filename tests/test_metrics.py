"""Tests for the metrics registry — uses a temp YAML file."""
import textwrap

import pytest

from askdata.metadata.metrics import MetricsRegistry


@pytest.fixture
def metrics_yaml(tmp_path):
    p = tmp_path / "metrics.yaml"
    p.write_text(
        textwrap.dedent(
            """
            metrics:
              复购率:
                description: 30 天内再次购买
                sql_template: SELECT 1
              月活:
                description: 当月活跃用户
                sql_template: SELECT 2
            """
        ),
        encoding="utf-8",
    )
    return str(p)


def test_search_finds_metric(metrics_yaml):
    reg = MetricsRegistry(config_path=metrics_yaml)
    hits = reg.search("复购率")
    assert len(hits) == 1
    assert hits[0]["name"] == "复购率"


def test_search_by_description(metrics_yaml):
    reg = MetricsRegistry(config_path=metrics_yaml)
    hits = reg.search("活跃")
    assert len(hits) == 1
    assert hits[0]["name"] == "月活"


def test_get_sql_template(metrics_yaml):
    reg = MetricsRegistry(config_path=metrics_yaml)
    assert "SELECT 1" in reg.get_sql_template("复购率")
