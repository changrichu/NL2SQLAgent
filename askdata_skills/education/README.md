# Education Skill

教育行业预置指标模板,涵盖**招生 / 学习行为 / 教学效果 / 续报 / 退课 / 教师产能**六大维度共 15 个核心指标。

## 覆盖的指标

| 分类 | 指标 |
|---|---|
| 招生 | 在读学员数、新增报名(当月)、课程招生排行 |
| 学习行为 | 学员日活、学员周活、平均学习时长、平均学习进度 |
| 教学效果 | 完课率、课程平均评分、NPS |
| 续报 | 续报率 |
| 退课 | 退课率(90天)、退款金额(当月) |
| 教师产能 | 课时消耗(当月)、教师课时统计 |

## 假设的表结构

```sql
courses(id, name, subject, level, started_at, ended_at, price)
enrollments(id, student_id, course_id, status, enrolled_at, refunded_at, progress)
students(id, name, email, grade, signup_at)
teachers(id, name, subject)
class_sessions(id, course_id, teacher_id, session_date, hours, status)
learning_events(id, student_id, course_id, event_type, duration_min, created_at)
course_feedback(id, student_id, course_id, score, comment, created_at)
```

## 行业参考值

| 指标 | 健康线 |
|---|---|
| 完课率 | K12 在线 > 60%, 职业培训 > 40% |
| 续报率 | > 50% 为良好 |
| NPS | > 30 为优秀 |
| 退课率 | < 10% 为健康 |
