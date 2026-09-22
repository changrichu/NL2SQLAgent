# E-commerce Skill

电商行业预置指标模板,涵盖**交易 / 流量 / 用户 / 商品 / 财务**五大维度共 17 个核心指标。

## 覆盖的指标

| 分类 | 指标 |
|---|---|
| 交易 | GMV、订单数(当日/当月)、客单价、客单价同比 |
| 流量 | 转化率(30天)、加购率、购物车放弃率 |
| 用户 | 复购率、月活买家、新客占比、RFM高价值客户、流失客户数 |
| 商品 | 热销商品 TOP10、热销品类 TOP5、渠道 GMV 分布 |
| 财务 | 退款率(30天)、退款金额(当月) |

## 假设的表结构

```sql
orders(id, user_id, amount, status, created_at, paid_at, refunded_at)
order_items(id, order_id, product_id, quantity, unit_price)
products(id, name, category_id, price, cost)
users(id, name, email, region, channel, created_at)
categories(id, name, parent_id)
page_views(id, user_id, page, created_at)
cart_items(id, user_id, product_id, quantity, created_at)
```

> ⚠️ 实际 schema 字段名不一致时,LLM 会按语义自动适配;若差异较大,可在 `metrics.yaml` 覆盖单条 SQL。

## 使用方法

```python
from askdata.agent.nl2sql_agent import NL2SQLAgent
from askdata.llm_client import LLMClient
from askdata.skills.registry import SkillRegistry
from askdata.metadata.metrics import MetricsRegistry

# 加载电商 skill 到 metrics 注册中心
metrics = MetricsRegistry()
SkillRegistry().apply_to_metrics_registry("ecommerce", metrics)

# 创建 Agent(已自带 17 个电商指标)
agent = NL2SQLAgent(llm=LLMClient(), datasource="postgres")
result = agent.run("上个月 GMV 多少?")
```
