# SQL Safety Design

## Why a separate module?

`askdata/sql/safety.py` is a pure-Python, dependency-free guard. It runs **inside
the connector** (not just at the agent layer) so that any caller — including a
buggy one — cannot execute unsafe SQL against the database.

## Layers

### Layer 1 — Keyword blacklist
```python
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
    "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "COPY", "VACUUM", "REINDEX",
}
```
Checked via `\bKEYWORD\b` so column names like `update_time` still pass.

### Layer 2 — Dangerous-pattern regex
| Pattern | Catches |
|---|---|
| `;\s*\w` | Stacked statements (`SELECT 1; DROP TABLE ...`) |
| `--` | SQL comments (injection vector) |
| `/\*` | Block comments |
| `\bOR\s+1\s*=\s*1` | Classic auth bypass |
| `\bUNION\s+SELECT\s+.*--` | Union-based injection |

### Layer 3 — First-token whitelist
Only statements starting with `SELECT` or `WITH` are allowed.

### Layer 4 — Auto LIMIT
Statements without `LIMIT` get `LIMIT 10000` appended.
Configurable via the `SQL_MAX_ROWS` env var.

## What it does NOT do (yet)

- **Field-level masking.** Planned for v0.2.0 via `sensitive_columns` config.
- **Row-level security.** Deferred to v0.3.0 with role-based schema filters.
- **Cost-based guards.** No timeout / cost cap on individual queries — add at
  the connection-pool layer.

## Testing

Run `pytest tests/test_safety.py -v` — 11 cases cover the blacklist,
whitelist, regex patterns, and auto-LIMIT logic.
