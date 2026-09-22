"""End-to-end demo: spin up an in-memory SQLite-like stand-in is overkill,
so we run the agent against a tiny SQLite database if available.

This is a runnable example, not a unit test.
"""
from __future__ import annotations

import os
import sys

# Allow running as `python examples/ecommerce_demo.py` from project root.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

import pandas as pd  # noqa: E402

from askdata.connectors.postgres import PostgresConnector  # noqa: E402
from askdata.metadata.metrics import MetricsRegistry  # noqa: E402
from askdata.metadata.schema_index import SchemaIndex  # noqa: E402


def main():
    print("🔎 AskData demo — introspecting the configured Postgres schema\n")

    connector = PostgresConnector()
    schema = connector.get_schema()
    if not schema:
        print("⚠️  No schema returned. Did you set POSTGRES_* env vars and is the DB reachable?")
        return

    df = pd.DataFrame(schema)
    print(df.head(20).to_string(index=False))

    print("\n🧠 Indexing schema and metrics registry…")
    idx = SchemaIndex(connector)
    metrics = MetricsRegistry()
    print(f"  - tables indexed: {len({r['table_name'] for r in schema})}")
    print(f"  - metrics loaded: {list(metrics.metrics.keys())}")

    print("\n🔍 Example retrieval: '复购率'")
    for m in metrics.search("复购率"):
        print(f"  - {m['name']}: {m.get('description', '')}")

    print("\n✅ Done. Set DEEPSEEK_API_KEY and POSTGRES_* and run `make api` to try the real agent.")


if __name__ == "__main__":
    main()
