"""Tests for the in-memory query history."""
from askdata.memory.query_history import QueryHistory


def test_add_and_recent():
    h = QueryHistory(max_size=10)
    h.add("q1", {"sql": "SELECT 1", "row_count": 1})
    h.add("q2", {"sql": "SELECT 2", "row_count": 2, "error": None})
    recent = h.recent(n=2)
    assert len(recent) == 2
    assert recent[0]["query"] == "q1"
    assert recent[1]["query"] == "q2"


def test_ring_buffer_respects_max_size():
    h = QueryHistory(max_size=3)
    for i in range(5):
        h.add(f"q{i}", {"sql": f"SELECT {i}"})
    assert len(h.recent(n=10)) == 3
