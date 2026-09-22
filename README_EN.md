# 💬 NL2SQLAgent · Natural-Language Data Analysis Agent

> **One sentence to query the whole company's data.** Business users ask in plain language, NL2SQLAgent writes safe SQL, runs it, and returns visualized results.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**English** | [简体中文](./README.md)

---

## ✨ Why NL2SQLAgent?

| Pain Point | Generic LLMs | **NL2SQLAgent** |
|---|---|---|
| Connect to enterprise DBs | ❌ No | ✅ Pluggable connectors (PG / MySQL / ClickHouse / Excel / API) |
| Unifying metric definitions | ❌ Inconsistent answers | ✅ Business metric registry (YAML) + SQL templates |
| SQL injection / data leakage | ⚠️ Human-dependent | ✅ Whitelist + auto-LIMIT + audit log |
| Locked into one LLM vendor | ⚠️ Rewrite prompts | ✅ Pluggable LLM provider, swap with one line |
| Non-technical users can't write SQL | ❌ | ✅ Natural-language chat |

---

## 🚀 Quick Start

```bash
git clone https://github.com/changrichu/NL2SQLAgent.git
cd NL2SQLAgent
pip install -r requirements.txt
cp .env.example .env       # fill in LLM key + DB credentials
make api                    # FastAPI on :8000
make ui                     # Streamlit on :8501
# or: docker compose up -d
```

---

## 💡 Example

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Repurchase rate of big customers in East China during Q3?", "datasource": "postgres"}'
```

Response:

```json
{
  "sql": "SELECT ... LIMIT 10000",
  "results": [{"repurchase_rate": 0.34}],
  "row_count": 1,
  "explanation": "Q3 East China big-customer repurchase rate is 34%, slightly up MoM."
}
```

Python:

```python
from askdata.agent.nl2sql_agent import NL2SQLAgent
from askdata.llm_client import LLMClient

agent = NL2SQLAgent(llm=LLMClient(), datasource="postgres")
print(agent.run("Daily order count over the last 7 days"))
```

---

## 🏗️ Architecture

```
Web UI / REST API / Python SDK
            │
            ▼
    ┌────────────────┐
    │  NL2SQL Agent  │  ReAct-style multi-step
    └────────┬───────┘
             │
   ┌─────────┼─────────┐
   ▼         ▼         ▼
 Schema    Metrics    LLM
  Index   Registry   (5 providers)
   │         │         │
   └────┬────┘         │
        ▼              │
   SQL Safety Guard    │
        ▼              │
   Pluggable Connectors
        ▼
   PG / MySQL / ClickHouse / Excel / API
```

---

## 🔐 SQL Safety

Four layers:

1. **Keyword whitelist** — only `SELECT` / `WITH` allowed
2. **Dangerous-pattern matcher** — blocks comments, stacked statements, OR-injection
3. **Auto-LIMIT** — appends `LIMIT 10000` if missing (configurable via `SQL_MAX_ROWS`)
4. **Audit log** — every query goes through `loguru`

Field-level masking planned for v0.2.0.

---

## 📊 Business Metric Registry

Centralize fuzzy metrics like "复购率" (repurchase rate) in `config/metrics.yaml`.
The agent prefers these templates over regenerating SQL from scratch.

---

## 🧪 Tests

```bash
make test
```

Coverage:
- `test_safety.py` — 11 SQL guard cases
- `test_schema_index.py` — schema search
- `test_metrics.py` — metric registry
- `test_query_history.py` — session history

All run without a real LLM or database.

---

## 🛣️ Roadmap

- [x] v0.1.0 — MVP: PG connector + multi-LLM + safety guard + Streamlit UI + REST API
- [ ] v0.2.0 — Field masking + persisted audit log + MySQL/ClickHouse
- [ ] v0.3.0 — Excel/CSV upload + role-based schema filter
- [ ] v0.4.0 — Multi-turn memory + query rewriter
- [ ] v0.5.0 — Golden set + Ragas evaluation loop

---

## 📜 License

[MIT](LICENSE) © 2026 changrichu
