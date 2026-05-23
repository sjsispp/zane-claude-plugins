# 验证文档模板（每轮）

> 本文件定义每轮验证文档的标准模板。验证文档一旦写入**不可修改**，修正只能体现在分析文档中。

---

## 文档模板

```markdown
# {链路名称} — Round {N} 数据验证

> 验证日期: {date}
> 轮次: Round {N}/3
> 分析文档版本: v{version}
> 采样订单: {packageId} (seller: {sellerId})

## 验证摘要

| 指标 | 值 |
|------|---|
| 总跳数 | {total_hops} |
| PASS | {pass} |
| FAIL | {fail} |
| 跳通过率 | {hop_rate}% |
| FK 违规 | {fk_violations} |
| 与上轮对比 | +{improved} / -{regressed} |

## 外键关系矩阵

| Step | 上游表 | FK 字段 | 关系 | 下游表 | FK 字段 | FK 类型 |
|------|--------|---------|------|--------|---------|---------|
| 0→1 | {表A} | {字段} | 1:N | {表B} | {字段} | 列FK |
| 1→2 | {表B} | {字段} | 1:1 | {表C} | {字段} | 跨模块列FK |
| 2→3 | {表C} | ext→{key} | 1:1 | {表D} | {字段} | JSON FK |

---

## Step {N}: {上游表} → {下游表}

**FK 关联**: `{上游表}.{字段}` = `{下游表}.{字段}` ({FK类型})

\```sql
-- [Step {N}] {描述}
-- DB: {database} | 索引: {index}
SELECT * FROM {下游表}
WHERE {fk_field} = '{上游值}'
  AND {shard_key} = '{shard_value}'
LIMIT 10;
\```

**验证结果**: ✅ PASS / ❌ FAIL

| 字段 | 值 | 校验 |
|------|-----|------|
| {字段1} | {值1} | {校验说明} |
| {字段2} | {值2} | {校验说明} |

---

(重复 Step 0 ~ Step N...)

---

## 跨步金额一致性校验

> 端到端校验关键金额字段在整个链路中的一致性。

| 字段 | Step 0 值 | Step N 值 | 一致性 |
|------|----------|----------|:------:|
| {金额字段1} | {值} | {值} | ✅/❌ |
| {金额字段2} | {值} | {值} | ✅/❌ |

## 时序校验

> 按 create_time 排列验证数据流转时序。

| Step | 表 | create_time | 与上一步间隔 |
|------|---|------------|------------|
| 0 | {表} | {时间} | -- |
| 1 | {表} | {时间} | {Xms} |

## 准出判定

| 条件 | 状态 |
|------|------|
| 3 轮完成 | {✅ Round N/3} |
| P0 全 PASS | {✅/❌ N 条 FAIL} |
| hop_rate >= 90% | {✅/❌ 当前 X%} |
| FK 合规 | {✅/❌ N 处违规} |
| **准出结论** | **{PASS/FAIL/PENDING}** |
```

---

## 使用说明

### 文件命名

```
{project}/docs/arch-analysis/verification/
├── round-1-verification.md    # Round 1（不可修改）
├── round-2-verification.md    # Round 2（不可修改）
├── round-3-verification.md    # Round 3（不可修改）
└── graduation-report.md       # 3 轮后准出报告
```

### 不可变性规则

1. `round-{N}-verification.md` 写入后**禁止修改**
2. 发现分析错误 → 修正分析文档 `chains/{chain}-analysis.md`
3. 下一轮验证文档记录与上一轮的 diff（改进/退化项）

### FK 类型标注规范

| FK 类型 | 标注 | 说明 |
|---------|------|------|
| 列FK | `列FK` | 两表同名列，有索引 |
| JSON FK | `JSON FK` | 上游 ext/extra JSON 字段包含下游 key |
| 跨模块列FK | `跨模块列FK` | 不同命名但语义相同（如 command_no ↔ request_no） |
| FORBIDDEN | `⛔ 泛化主键` | package_id/order_id/biz_no — 禁止使用 |

### Round 间 diff 记录

Round 2+ 文档应在摘要部分记录与上轮的对比:

```markdown
## 与 Round {N-1} 对比

| 变化类型 | Step | 说明 |
|---------|------|------|
| 修复 | Step 2→3 | FK 从 package_id 修正为 record_no，现在 PASS |
| 退化 | Step 5→6 | 分析文档修正后 amount 不匹配 |
| 新增 | Step 7→8 | 分析文档新增的链路跳 |
```
