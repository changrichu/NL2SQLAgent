"""Tests for the in-memory schema index — uses a fake connector, no DB."""
from askdata.connectors.base import BaseConnector
from askdata.metadata.schema_index import SchemaIndex


class FakeConnector(BaseConnector):
    name = "fake"

    def __init__(self, schema):
        self._schema = schema

    def execute_readonly(self, sql, params=None):
        return []

    def get_schema(self):
        return self._schema


def test_search_finds_matching_table():
    schema = [
        {"table_name": "orders", "column_name": "user_id", "data_type": "int"},
        {"table_name": "orders", "column_name": "amount", "data_type": "numeric"},
        {"table_name": "users", "column_name": "email", "data_type": "text"},
    ]
    idx = SchemaIndex(FakeConnector(schema))
    hits = idx.search("orders by amount", top_k=5)
    assert hits
    assert hits[0]["table_name"] == "orders"


def test_search_returns_empty_for_unrelated_query():
    schema = [{"table_name": "orders", "column_name": "id", "data_type": "int"}]
    idx = SchemaIndex(FakeConnector(schema))
    assert idx.search("weather in tokyo", top_k=5) == []
