# AskData Architecture

## High-level flow

```
User question
     │
     ▼
┌───────────────────────────────┐
│ 1. Schema Index  (top-k=5)   │  ← information_schema.columns
└────────────┬──────────────────┘
             ▼
┌───────────────────────────────┐
│ 2. Metric Registry search     │  ← config/metrics.yaml
└────────────┬──────────────────┘
             ▼
┌───────────────────────────────┐
│ 3. LLM  ── SQL generation    │  ← NL2SQL_SYSTEM_PROMPT + schema + metrics
└────────────┬──────────────────┘
             ▼
┌───────────────────────────────┐
│ 4. SQL Safety Guard          │  ← keyword whitelist + dangerous patterns + LIMIT
└────────────┬──────────────────┘
             ▼
┌───────────────────────────────┐
│ 5. Connector execute_readonly│  ← pluggable per datasource
└────────────┬──────────────────┘
             ▼
┌───────────────────────────────┐
│ 6. LLM  ── explanation       │  ← EXPLAIN_SYSTEM_PROMPT
└────────────┬──────────────────┘
             ▼
        Return JSON
```

## Component contracts

### `LLMClient`
- `chat(prompt, system=None, temperature=0.1) -> str`
- One SDK (`openai`), five providers behind it.

### `BaseConnector`
- `execute_readonly(sql, params=None) -> List[Dict]`
- `get_schema() -> List[Dict]`
- `get_sample(table, n=3) -> List[Dict]` (inherited)
- `close()` (no-op by default)

### `MetricsRegistry`
- `search(query) -> List[Dict]`  (keyword match on name + description)
- `get_sql_template(name) -> str`
- `reload()` — re-read YAML on hot-reload

### `SchemaIndex`
- `refresh()` — pull schema from connector
- `search(query, top_k) -> List[Dict]` — keyword score over table+column names

### `SQLSafety`
- `is_safe(sql) -> bool`
- `add_limit(sql, max_rows) -> str`

### `NL2SQLAgent`
- `run(query, user_id) -> Dict` — returns `{sql, results, row_count, explanation}`
- On safety failure: `{error, sql}`
- On execution failure: `{error, sql}`

## Why this design?

1. **Pluggability first.** LLM and connectors are both behind registries, so new
   providers / datasources slot in without rewriting the agent.
2. **Safety is a precondition, not an after-thought.** `SQLSafety.is_safe` runs
   inside the connector itself, so even a buggy caller cannot bypass it.
3. **Metrics live in YAML, not code.** PM/ops can update shared definitions
   without PR review on the agent code path.
4. **No premature abstractions.** Schema index is keyword search today; swap
   it for vector search tomorrow without touching the agent's `run()`.

## Threat model

| Threat | Mitigation |
|---|---|
| Prompt injection makes LLM emit `DROP TABLE` | SQLSafety.is_safe rejects it |
| LLM emits `; DROP TABLE users` | Stacked-statement regex blocks it |
| LLM emits `WHERE 1=1 OR password IS NOT NULL` | OR-injection regex blocks it |
| User runs `SELECT * FROM huge_table` | Auto-LIMIT caps row count |
| API key leaks to git | `.env` is gitignored; CI fails on `grep` of `.env` |
