# 💬 NL2SQLAgent · 自然语言驱动的企业数据分析Agent

> **一句话查全公司数据** —— 业务人员用自然语言提问,Agent 自动生成 SQL、安全执行、返回可视化结果。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[English](./README_EN.md) | **简体中文**

---

## ✨ 为什么需要 NL2SQLAgent?

| 痛点 | 豆包 / 通用 ChatGPT | **NL2SQLAgent** |
|---|---|---|
| 连不上企业数据库 | ❌ 只能回答通用问题 | ✅ 通过连接器直接对接 PG/MySQL/ClickHouse |
| "复购率"等口径不统一 | ❌ 每次问得不一样 | ✅ 业务指标中台(YAML)+ SQL 模板 |
| SQL 注入 / 数据越权 | ⚠️ 取决于人 | ✅ 白名单 + 强制 LIMIT + 字段脱敏 |
| 切换模型被厂商绑定 | ⚠️ 改 Prompt 重写 | ✅ LLM Provider 抽象,1 行切换 |
| 业务人员不会 SQL | ❌ 用不上 | ✅ 自然语言对话 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/changrichu/NL2SQLAgent.git
cd NL2SQLAgent
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env,填入 LLM API Key 和数据库连接
```

`.env` 关键字段:

```bash
LLM_PROVIDER=deepseek          # openai | deepseek | qwen | doubao | zhipu
DEEPSEEK_API_KEY=sk-xxx        # 跟 provider 对应的 key
POSTGRES_HOST=localhost
POSTGRES_DB=askdata_demo
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### 3. 启动 API

```bash
make api
# 访问 http://localhost:8000/docs 看 OpenAPI 文档
```

### 4. 启动 Web UI

```bash
make ui
# 访问 http://localhost:8501
```

### 5. 一键启动所有服务(含 Postgres)

```bash
docker compose up -d
```

---

## 💡 使用示例

### REST API

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Q3 华东区大客户复购率多少?", "datasource": "postgres"}'
```

返回:

```json
{
  "sql": "SELECT ... LIMIT 10000",
  "results": [{"repurchase_rate": 0.34}],
  "row_count": 1,
  "explanation": "Q3 华东区大客户的复购率为 34%,环比上月略有上升。"
}
```

### Python 调用

```python
from askdata.agent.nl2sql_agent import NL2SQLAgent
from askdata.llm_client import LLMClient

agent = NL2SQLAgent(llm=LLMClient(), datasource="postgres")
result = agent.run("最近 7 天每天的订单数")
print(result["sql"])
print(result["results"])
print(result["explanation"])
```

---

## 🏗️ 架构

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Streamlit   │    │   FastAPI    │    │  Python SDK  │
│   Web UI     │    │   REST API   │    │              │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       └──────────────────┬┴──────────────────┘
                          ▼
              ┌──────────────────────┐
              │     NL2SQL Agent     │
              │ (ReAct 风格多步推理) │
              └──────────┬───────────┘
                         ▼
        ┌────────────────┼─────────────────┐
        ▼                ▼                 ▼
  ┌──────────┐    ┌──────────────┐   ┌──────────┐
  │  Schema  │    │   Metrics    │   │   LLM    │
  │  Index   │    │  Registry    │   │ Provider │
  └────┬─────┘    └──────┬───────┘   │ 抽象层   │
       │                 │           └────┬─────┘
       │                 │                ▼
       │                 │     OpenAI / DeepSeek / Qwen /
       │                 │       豆包 / 智谱 GLM
       │                 │
       ▼                 ▼
  ┌────────────────────────────┐
  │     SQL Safety Guard       │
  │  (白名单 + LIMIT + 脱敏)   │
  └────────────┬───────────────┘
               ▼
  ┌────────────────────────────┐
  │   Pluggable Connectors     │
  │  PostgreSQL · MySQL ·      │
  │  ClickHouse · Excel · API  │
  └────────────────────────────┘
```

---

## 🧩 核心模块

| 模块 | 作用 |
|---|---|
| `llm_client.py` | LLM Provider 抽象,支持 OpenAI/DeepSeek/Qwen/**豆包**/智谱 一键切换 |
| `agent/nl2sql_agent.py` | 主 Agent:检索 Schema → 检索指标 → 生成 SQL → 安全检查 → 执行 → 解释 |
| `metadata/schema_index.py` | 表/字段元数据索引,基于关键字检索相关表 |
| `metadata/metrics.py` | 业务指标中台,YAML 维护,产品经理也能改 |
| `sql/safety.py` | SQL 安全沙箱:关键字白名单 + 危险模式匹配 + 自动加 LIMIT |
| `connectors/postgres.py` | PostgreSQL 连接器(只读 + 安全 guard) |
| `connectors/{mysql,clickhouse,excel,api}.py` | 占位实现,按需扩展 |
| `web_ui/streamlit_app.py` | Streamlit 对话式 UI,自动出表 + 自动画图 |
| `main.py` | FastAPI 入口,暴露 `/query` `/health` `/history` |

---

## 🔐 SQL 安全设计

四道防线:

1. **关键字白名单**:只允许 `SELECT`/`WITH` 开头,禁止 `INSERT/UPDATE/DELETE/DROP/ALTER/...`
2. **危险模式匹配**:拦截 `--` 注释、`;` 堆叠语句、`OR 1=1` 注入
3. **强制 LIMIT**:没有 LIMIT 自动补 `LIMIT 10000`(可在 `.env` 调 `SQL_MAX_ROWS`)
4. **审计日志**:所有查询通过 `loguru` 落盘,出错立即可见

字段脱敏(planned v0.2.0):在 `connectors/` 里加入 `sensitive_columns` 配置,自动 mask。

---

## 📊 业务指标中台

把"复购率"这种每个部门都算得不一样的指标,集中到 `config/metrics.yaml`:

```yaml
metrics:
  复购率:
    description: 30 天内再次购买的客户比例
    sql_template: |
      SELECT
        COUNT(DISTINCT CASE WHEN order_count >= 2 THEN user_id END)::float
        / NULLIF(COUNT(DISTINCT user_id), 0) AS repurchase_rate
      FROM (...)
```

业务人员改 YAML 就能调口径,不用动代码。Agent 在生成 SQL 时会优先复用这些已定义好的模板。

---

## 🧪 测试

```bash
make test
```

测试覆盖:
- `tests/test_safety.py` — SQL 安全 guard 11 个用例
- `tests/test_schema_index.py` — Schema 检索
- `tests/test_metrics.py` — 指标注册中心
- `tests/test_query_history.py` — 会话历史

不需要真实的 LLM 或数据库即可全部跑通(LLM 和 DB 走 fake/stub)。

---

## 📁 项目结构

```
askdata/
├── src/askdata/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 配置(LLM Provider、数据库)
│   ├── llm_client.py            # ⭐ LLM 统一接口
│   ├── agent/
│   │   ├── __init__.py
│   │   └── nl2sql_agent.py      # Text-to-SQL 主体
│   ├── connectors/              # ⭐ 数据源连接器
│   │   ├── base.py
│   │   ├── postgres.py
│   │   ├── mysql.py
│   │   ├── clickhouse.py
│   │   ├── excel.py
│   │   └── api.py
│   ├── metadata/                # ⭐ 元数据层
│   │   ├── schema_index.py
│   │   └── metrics.py
│   ├── sql/                     # ⭐ SQL 安全
│   │   └── safety.py
│   ├── memory/
│   │   └── query_history.py
│   ├── web_ui/
│   │   └── streamlit_app.py
│   └── prompts/
│       └── templates.py
├── config/
│   ├── datasources.yaml
│   └── metrics.yaml
├── examples/
│   └── ecommerce_demo.py
├── tests/
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🛣️ 路线图

- [x] v0.1.0 — MVP:PG 连接器 + 多 LLM + 安全 guard + Streamlit UI + REST API
- [ ] v0.2.0 — 字段脱敏 + 审计日志落盘 + MySQL/ClickHouse 连接器
- [ ] v0.3.0 — Excel/CSV 上传 + 业务用户权限(基于角色的 Schema 过滤)
- [ ] v0.4.0 — 多轮对话记忆 + Query 改写(Rewriter)
- [ ] v0.5.0 — 黄金集 + Ragas 评估闭环

---

## 🤝 跟 MemoryAgent 的关系

| | MemoryAgent | NL2SQLAgent |
|---|---|---|
| 任务 | 对话(回答问题) | 数据查询(执行 SQL) |
| 触发 | 用户提问 → 检索知识 | 用户提问 → 跑 SQL |
| 记忆 | 三层(L1/L2/L3)+ Graph | 会话历史 + 用户偏好 |
| 核心 | RAG + Agentic Loop | NL2SQL + 安全沙箱 |

两个项目组合起来,完整覆盖"AI 产品经理"的能力画像 —— 既能跟用户聊,又能查数据。

---

## 📜 License

[MIT](LICENSE) © 2026 changrichu

---

## ⭐ Star History

如果这个项目对你有帮助,欢迎点个 Star ⭐ 鼓励作者继续迭代!
