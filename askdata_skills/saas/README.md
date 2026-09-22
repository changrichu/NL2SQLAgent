# SaaS Skill

SaaS 行业预置指标模板,涵盖 **增长(Acquisition)/ 活跃(Activation)/ 留存(Retention)/ 变现(Revenue)/ 健康度(Health)** 共 19 个核心指标。

## 覆盖的指标

| 分类 | 指标 |
|---|---|
| 增长 | 新增注册(当日/当月)、付费转化率 |
| 活跃 | DAU、MAU、WAU、DAU/MAU 比 |
| 留存 | D7 留存率、D30 留存率 |
| 变现 | ARPU、ARPPU、MRR、ARR、LTV、LTV/CAC 比 |
| 健康度 | Churn 率(月)、NPS、客诉率、工单平均解决时长 |

## 假设的表结构

```sql
users(id, email, signup_at, channel, country)
events(id, user_id, event_name, created_at, properties)
subscriptions(id, user_id, plan, amount, status, started_at, cancelled_at, mrr)
surveys(id, user_id, score, created_at)
support_tickets(id, user_id, created_at, resolved_at, priority)
user_acquisition(user_id, channel, marketing_spend, acquired_at)
```

## 核心公式

| 指标 | 公式 |
|---|---|
| LTV/CAC | 累计收入 / 获客成本,>3 优秀, <1 危险 |
| DAU/MAU | 反映粘性,>20% 优秀 |
| Churn | (流失数 / 期初活跃数),<5% 优秀 |
| MRR → ARR | MRR × 12 |
