# NL2SQLAgent Roadmap

## v0.1.0 — MVP ✅
- LLM Provider abstraction (OpenAI / DeepSeek / Qwen / 豆包 / 智谱)
- PostgreSQL connector with read-only enforcement
- SQL safety guard (keyword whitelist + dangerous-pattern regex + auto-LIMIT)
- Schema index (in-memory keyword search)
- Business metric registry (YAML + SQL templates)
- Streamlit chat UI with auto bar chart
- FastAPI `/query` `/health` `/history`
- Unit tests covering safety / schema / metrics / history

## v0.2.0 — Security hardening
- Field-level masking via `sensitive_columns` config
- Persisted audit log (SQLite / file rotation)
- Query result caching by `(sql_hash, user_id)`
- MySQL + ClickHouse connectors (real implementations)

## v0.3.0 — Authoring for business users
- Excel/CSV upload connector
- Role-based schema filtering (user role → table allow-list)
- Simple web admin for editing `metrics.yaml`

## v0.4.0 — Conversational depth
- Multi-turn memory (rewrite follow-up questions against prior context)
- Query clarification prompt when schema is ambiguous
- ReAct loop with explicit Thought / Action / Observation trace

## v0.5.0 — Evaluation & observability
- Golden test set with `(query, expected_sql, expected_results)` triples
- Ragas / LLM-as-Judge scoring pipeline
- OpenTelemetry traces for every agent run

## Backlog ideas
- DuckDB connector for local file analysis
- Streaming responses for large result sets
- Slack / 飞书 bot adapter
- MCP server exposing `askdata.query` as a tool
