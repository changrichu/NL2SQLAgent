"""Tests for the chart recommender heuristic."""
from datetime import date, datetime
from decimal import Decimal

from askdata.tools.chart_recommender import recommend_chart


def test_empty_results():
    rec = recommend_chart([])
    assert rec["chart_type"] == "empty"


def test_single_numeric_kpi_card():
    rec = recommend_chart([{"amount": 1234}])
    assert rec["chart_type"] == "kpi_card"
    assert rec["x"] == "amount"


def test_time_series_line():
    rows = [
        {"month": "2026-01", "gmv": 100},
        {"month": "2026-02", "gmv": 200},
    ]
    rec = recommend_chart(rows)
    assert rec["chart_type"] == "line"
    assert rec["x"] == "month"
    assert rec["y"] == "gmv"


def test_category_bar():
    """Category + numeric with > 8 rows -> bar (pie only for small breakdowns)."""
    rows = [{"region": f"R{i}", "sales": i} for i in range(10)]
    rec = recommend_chart(rows)
    assert rec["chart_type"] == "bar"
    assert rec["x"] == "region"
    assert rec["y"] == "sales"


def test_small_category_pie():
    rows = [
        {"channel": "App", "share": 0.4},
        {"channel": "Web", "share": 0.3},
        {"channel": "WeChat", "share": 0.3},
    ]
    rec = recommend_chart(rows)
    assert rec["chart_type"] == "pie"


def test_large_category_still_bar():
    rows = [{"region": f"R{i}", "sales": i} for i in range(20)]
    rec = recommend_chart(rows)
    assert rec["chart_type"] == "bar"


def test_two_numeric_scatter():
    rows = [
        {"age": 25, "income": 5000},
        {"age": 30, "income": 8000},
    ]
    rec = recommend_chart(rows)
    assert rec["chart_type"] == "scatter"


def test_three_columns_table():
    """3 columns, first one is time -> line chart (multi-series over time)."""
    rows = [
        {"date": "2026-01", "region": "华东", "sales": 100},
    ]
    rec = recommend_chart(rows)
    assert rec["chart_type"] == "line"


def test_three_columns_no_time_table():
    """3 columns without any time -> fallback to table."""
    rows = [
        {"region": "华东", "category": "大客户", "sales": 100},
    ]
    rec = recommend_chart(rows)
    assert rec["chart_type"] == "table"


def test_decimal_values_handled():
    rows = [{"price": Decimal("99.99")}]
    rec = recommend_chart(rows)
    assert rec["chart_type"] == "kpi_card"


def test_datetime_values_handled():
    rows = [{"created_at": datetime(2026, 9, 23), "gmv": 100}]
    rec = recommend_chart(rows)
    assert rec["chart_type"] == "line"
