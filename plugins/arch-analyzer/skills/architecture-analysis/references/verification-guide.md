# 验证方法论参考

> 本文件定义架构分析数据验证的方法论，供 `/arch-verify` 命令使用。

---

## 断言设计规则

### 基本原则

1. **一条断言 = 一次工具调用**: 每条断言必须可通过一次 MCP 工具调用验证
2. **可重复执行**: 断言必须是确定性的，多次执行结果一致
3. **有明确预期**: 每条断言必须有明确的"预期值"和"比较方式"
4. **独立性**: 断言之间不应有执行顺序依赖

### 断言命名规范

```
{类别}-{序号} [{优先级}] {描述}

示例:
V-TOPO-01 [P0] 上游服务 luna-service 调用本服务
V-DATA-03 [P1] 表 t_settlement_record 有数据
V-CFG-02 [P2] Apollo key settle.timeout 值为 30000
```

### 优先级定义

| 优先级 | 含义 | 验证要求 |
|--------|------|---------|
| **P0** | 必验 — 分析核心结论 | 必须 PASS，FAIL 则分析结论不可信 |
| **P1** | 重要 — 关键支撑数据 | 应当 PASS，FAIL 需要 REFACTOR |
| **P2** | 补充 — 辅助验证 | 建议 PASS，FAIL 可标注说明 |

### P0 断言分配指南

| 分析层 | P0 断言范围 | 说明 |
|--------|------------|------|
| L0 | 核心上下游关系 + 主要入口有流量 | 服务全景的基础事实 |
| L3 | 核心链路涉及的表关联 | 链路分析的数据基础 |
| L5 | 核心表存在且有数据 | 数据模型的事实基础 |

---

## 从分析层级自动生成断言

### L0 服务全景 → V-TOPO + V-ENTRY

**V-TOPO 生成规则**:
- 对 L0 上游调用统计表的每行: 生成 `V-TOPO-{N} 上游服务 {callerApp} 调用方法 {method}`
- 对 L0 下游依赖统计表的每行: 生成 `V-TOPO-{N} 下游依赖 {targetApp} 接口 {interface}`

**V-ENTRY 生成规则**:
- 对 L0 服务入口统计表的 TOP3 接口: 生成 `V-ENTRY-{N} 入口 {type}:{name} 有流量`

### L2 业务全景 → V-MQ + V-CFG

**V-MQ 生成规则**:
- 对 L2 触发来源中的 MQ 类型: 生成 `V-MQ-{N} Topic {topic} 有消息流转`

**V-CFG 生成规则**:
- 对 L2 业务身份体系中的关键配置: 生成 `V-CFG-{N} Apollo {key} 存在`

### L3 核心链路 → V-FLOW + V-REL

**V-FLOW 生成规则**:
- 对每条核心链路的入口: 生成 `V-FLOW-{N} 链路 {name} 入口 {method} 有 XRay trace`
- 对链路涉及的关键步骤: 生成 `V-FLOW-{N} 步骤 {step} 在 trace 中可观测`

**V-REL 生成规则**:
- 对数据流转表中的每对表: 生成 `V-REL-{N} 表 {table1} → {table2} 通过 {field} 关联`

### L4 技术流程 → V-STS

**V-STS 生成规则**:
- 对状态机中的每个状态: 生成 `V-STS-{N} 表 {table} 存在状态 {status}`
- 对关键状态流转: 生成 `V-STS-{N} 状态 {from} → {to} 在数据中可观测`

### L5 数据模型 → V-DATA

**V-DATA 生成规则**:
- 对核心表清单中的每张表: 生成 `V-DATA-{N} 表 {table} 存在且有数据`
- 对表结构中的关键字段: 生成 `V-DATA-{N} 表 {table} 字段 {field} 类型为 {type}`

### L6 配置扩展 → V-CFG

**V-CFG 生成规则**:
- 对核心配置项表的每行: 生成 `V-CFG-{N} Apollo {key} = {expected_value}`

---

## 验证组分配规则

### G1: 拓扑+入口 (V-TOPO + V-ENTRY)

**目标**: 验证服务的外部连接关系
**验证工具**: batch_query_upstream, batch_query_downstream, query_rpc_topology
**预期断言数**: 15-20
**通过标准**: P0 全部 PASS，总通过率 >= 90%

### G2: 数据+关联 (V-DATA + V-REL)

**目标**: 验证数据模型的事实基础
**验证工具**: execute_dms_sql_query, get_cached_table_schema
**预期断言数**: 15-20
**通过标准**: 核心表全部存在，关联关系 >= 80% 验证

### G3: 配置+消息+调度 (V-CFG + V-MQ + V-JOB)

**目标**: 验证运行时配置和异步处理
**验证工具**: get_apollo_config_value, query_mq_by_key, list_jobs
**预期断言数**: 10-15
**通过标准**: 配置项存在且值匹配 >= 90%

### G4: 核心流程 (V-FLOW)

**目标**: 验证业务流程按文档执行
**验证工具**: query_xray_logs + execute_dms_sql_query
**预期断言数**: 10-15
**通过标准**: 核心链路全部可追踪

### G5: 状态+边缘 (V-STS + 边缘场景)

**目标**: 验证状态机和边缘场景
**验证工具**: execute_dms_sql_query
**预期断言数**: 5-10
**通过标准**: 状态枚举 >= 80% 可观测

---

## 双文档交替驱动方法论（v4.0）

> 取代 v3.0 的 RED/GREEN/REFACTOR 单文档模式。核心变化: 分析文档和验证文档分离，交替驱动 3 轮强制迭代。

### 核心原则

1. **分析文档可修正**: `chains/{chain}-analysis.md` 根据验证发现持续修正
2. **验证文档不可变**: `round-{N}-verification.md` 写入后禁止修改
3. **3 轮强制**: 不是上限，是强制要求，每轮独立
4. **交替驱动**: 分析 → 验证 → 修正分析 → 再验证

### 3 轮验证流程

| 轮次 | 输入 | 目标 | 产出 |
|------|------|------|------|
| Round 1 | Step 4 分析文档 | 初始验证，发现分析偏差 | round-1-verification.md |
| Round 2 | Round 1 修正后的分析文档 | 确认修复有效，检测回归 | round-2-verification.md |
| Round 3 | Round 2 修正后的分析文档 | 全量回归，确保无退化 | round-3-verification.md |

### 每轮执行步骤

1. 读取当前版本的分析文档
2. 对每条链路的每一跳:
   a. 查表结构确定 FK 字段
   b. 按 FK 优先级选择关联键（禁止泛化主键）
   c. 生成 FK-first SQL（含 DB、索引、分片键）
   d. 执行 DMS 查询验证
   e. 记录: SQL + 结果 + FK类型 + PASS/FAIL
3. 执行跨步金额一致性校验
4. 执行时序校验（create_time 排列）
5. 输出 `round-{N}-verification.md`（不可修改）
6. 汇总: 跳通过率、FK 合规率、FAIL 项列表
7. 基于 FAIL 项修正分析文档（标注 diff）

### 验证文档不可变性规则

- `round-{N}-verification.md` 写入后**禁止修改**
- 修正只能体现在分析文档 `chains/{chain}-analysis.md` 中
- 下一轮验证文档记录与上一轮的 diff（改进/退化项）

### FAIL 分类处理（轮次内）

| FAIL 类型 | 处理方式 | 体现位置 |
|----------|---------|---------|
| 分析结论错误 | 修正分析文档对应章节 | 分析文档 diff |
| FK 选择错误 | 修正 FK 关联为更精确的列 | 分析文档 + 下轮验证 |
| 数据不存在 | 换采样订单或查询条件 | 下轮验证重试 |
| 工具不可用 | 标注 SKIP + 原因 | 当前验证文档 |
| 新发现 | 补充到分析文档 | 分析文档 + 下轮验证 |

---

## FK 优先级层级

> 每跳关联必须使用最精确的 FK，禁止使用泛化主键。

### 优先级

| 优先级 | FK 类型 | 说明 | 示例 |
|--------|---------|------|------|
| **P1** | 列 FK | 两表存在同名列且有索引 | `record_no = record_no` |
| **P2** | JSON FK | 上游表 ext/extra JSON 字段包含下游表 key | `ext→settlementRecordNo = record_no` |
| **P3** | 跨模块列 FK | 不同命名但语义相同 | `command_no = request_no` |
| **⛔** | 泛化主键 | package_id / order_id / biz_no 等 | 禁止用于跳间关联 |

### FK 发现流程

```
1. get_cached_table_schema(上游表) → 获取列名+索引
2. get_cached_table_schema(下游表) → 获取列名+索引
3. 查找同名列（优先有索引的列）→ 找到则为 P1 列FK
4. 未找到 → 检查上游表 ext/extra/biz_extra_info 等 JSON 列
   → 解析 JSON 键，匹配下游表列名 → 找到则为 P2 JSON FK
5. 仍未找到 → 搜索代码确认跨模块映射关系
   → 如 command_no 在代码中赋值给 request_no → P3 跨模块FK
6. 仅剩 package_id/order_id/biz_no → ⛔ FK 违规，自动 FAIL
```

### FK 违规处理

- 使用泛化主键的跳**自动标记为 FAIL**
- FK 违规计入准出门禁（fk_violation_count 必须为 0）
- FAIL 后必须在分析文档中修正 FK 关联

---

## 准出门禁

> 3 轮验证完成后，执行准出检查。4 条件全部通过才算 PASS。

### 门禁条件

```
rounds_completed == 3       AND    # 3 轮强制
P0_assertions ALL PASS      AND    # P0 断言全通过
hop_pass_rate >= 90%         AND    # 跳通过率 >= 90%
fk_violation_count == 0             # FK 合规
```

### 门禁逻辑

```
if (round_count < 3):
    → FAIL: "强制 3 轮，当前仅 {N} 轮"
if (any P0 assertion FAIL in Round 3):
    → FAIL: "{N} 条 P0 断言失败"
if (Round 3 hop_pass_rate < 90%):
    → FAIL: "跳通过率 {rate}% < 90%"
if (Round 3 fk_violations > 0):
    → FAIL: "{N} 处 FK 违规"
All pass:
    → PASS: 生成 graduation-report.md
```

### 门禁输出

通过时生成 `verification/graduation-report.md`：
- 3 轮验证摘要对比
- 最终 FK 关系矩阵
- 准出结论

---

## 验证文档模板

每轮验证文档的标准模板参考 `references/verification-doc-template.md`。

### 关键模板组件

| 组件 | 说明 |
|------|------|
| 验证摘要 | 总跳数、PASS/FAIL、跳通过率、FK 违规数 |
| 外键关系矩阵 | 全链路 FK 类型总览 |
| 逐跳验证 | 每跳: FK 关联 + SQL + 结果表 |
| 跨步金额校验 | 端到端金额一致性 |
| 时序校验 | create_time 排列 |
| 准出判定 | 4 条件检查 |
