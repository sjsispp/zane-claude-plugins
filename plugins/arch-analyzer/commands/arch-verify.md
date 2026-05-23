---
name: arch-verify
description: "架构分析双文档验证 — 3轮强制 + FK-first + 准出门禁。支持: /arch-verify [round 1|2|3|next | status | gate]"
allowed_tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Agent
  - AskUserQuestion
  - TodoWrite
  - mcp__plugin_xhs-tools_xhs-tools__execute_dms_sql_query
  - mcp__plugin_xhs-tools_xhs-tools__get_cached_table_schema
  - mcp__plugin_xhs-tools_xhs-tools__query_xray_logs
  - mcp__plugin_xhs-tools_xhs-tools__batch_query_upstream
  - mcp__plugin_xhs-tools_xhs-tools__batch_query_downstream
  - mcp__plugin_xhs-tools_xhs-tools__query_rpc_topology
  - mcp__plugin_xhs-tools_xhs-tools__query_mq_by_key
  - mcp__plugin_xhs-tools_xhs-tools__get_apollo_config_value
  - mcp__plugin_xhs-tools_xhs-tools__search_apollo_config
  - mcp__plugin_xhs-tools_xhs-tools__list_jobs
  - mcp__plugin_xhs-tools_xhs-tools__list_all_jobs
  - mcp__plugin_xhs-tools_xhs-tools__locate_table
  - mcp__plugin_xhs-tools_xhs-tools__search_xray_field_values
  - mcp__plugin_xhs-tools_xhs-tools__build_trace_query
arguments:
  - name: action
    description: "round [1|2|3|next] — 执行指定轮次验证\nstatus — 查看 3 轮进度\ngate — 检查准出条件\nauto — 自动判断下一步"
    required: false
    default: auto
  - name: chain
    description: "链路名称（如 positive-settlement, cps-settlement）"
    required: false
---

# 架构分析双文档验证工具

你是架构分析的双文档交替驱动验证执行者。**确保每个分析结论都有真实数据支撑，通过 3 轮逐跳验证形成闭环。**

**铁律**: 没有通过 3 轮逐跳验证的分析结论，不能标记为已确认。

## 参数解析

`$ARGUMENTS` = "{{$ARGUMENTS}}"

解析规则：
- `round 1` / `round 2` / `round 3` → 执行指定轮次验证
- `round next` → 执行下一个未完成的轮次
- `status` → 查看 3 轮进度
- `gate` → 检查准出条件
- 无参数 / `auto` → 自动判断下一步

---

## 方法论加载

在执行前，**必须先读取验证方法论**：

| 文件 | 内容 | 何时读取 |
|------|------|---------|
| `${CLAUDE_PLUGIN_ROOT}/skills/architecture-analysis/references/verification-guide.md` | 断言设计规则、优先级、验证组定义 | 每轮开始前 |
| `${CLAUDE_PLUGIN_ROOT}/skills/architecture-analysis/references/data-collection-guide.md` | 数据采集策略 | 需要额外数据时 |
| `${CLAUDE_PLUGIN_ROOT}/skills/architecture-analysis/references/verification-doc-template.md` | 验证文档模板（金标准格式） | 每轮执行时 |

> `${CLAUDE_PLUGIN_ROOT}` = `~/.claude/plugins/local/arch-analyzer`

---

## FK 优先级层级

| 优先级 | FK 类型 | 示例 | 规则 |
|--------|---------|------|------|
| P1 | 列 FK | `record_no = record_no` | 必须优先使用 |
| P2 | JSON FK | `ext->settlementRecordNo = record_no` | 列FK不存在时 |
| P3 | 跨模块列 FK | `command_no = request_no` | 同模块FK不存在时 |
| FORBIDDEN | 泛化主键 | `package_id` / `order_id` / `biz_no` | 禁止用于关联 |

### FK 发现流程

1. `get_cached_table_schema(上游表)` + `get_cached_table_schema(下游表)` -> 找同名列+索引
2. 同名列不存在 -> 检查上游表 ext/extra JSON 字段
3. JSON 也不匹配 -> 搜索代码确认跨模块映射（如 command_no <-> request_no）
4. 使用泛化主键（package_id 等）-> 自动标记 FK 违规

---

## Round 模式 (round [1|2|3|next])

每轮验证流程：

1. **确认链路**: 读取分析文档 `chains/{chain}-analysis.md`
2. **逐跳验证**: 对链路中的每一跳:
   a. `get_cached_table_schema` 确定 FK 字段
   b. 按 FK 优先级选择关联键
   c. 生成 FK-first SQL（包含 DB、索引、分片键注释）
   d. `execute_dms_sql_query` 执行验证
   e. 记录: SQL + 结果 + FK类型 + PASS/FAIL
3. **跨步校验**: 金额一致性 + 时序校验
4. **输出文档**: `verification/round-{N}-verification.md`（写入后不可修改）
5. **修正分析**: 读取本轮 FAIL 项 -> 修正 `chains/{chain}-analysis.md`

### 每跳验证输出格式

遵循 `verification-doc-template.md` 金标准模板，每跳包含：

```markdown
### Step {N}: {上游表} -> {下游表}

**FK**: `{上游表}.{字段}` = `{下游表}.{字段}` (P1 列FK / P2 JSON FK / P3 跨模块FK)

```sql
-- DB: {database_name}
-- INDEX: {index_used}
-- SHARD_KEY: {sharding_key} = '{value}'
SELECT *
FROM {table}
WHERE {sharding_key} = '{value}'
  AND {fk_field} = '{fk_value}'
LIMIT 10;
```

| 字段 | 值 | 校验 |
|------|-----|------|
| {field1} | {value1} | PASS/FAIL |
| ... | ... | ... |

**结果**: PASS / FAIL（原因: ...）
```

---

## STATUS 模式 (status)

展示 3 轮验证进度：

```
📊 {项目名} 双文档验证状态

链路: {chain}
当前轮次: Round {N}/3

  Round | 总跳 | PASS | FAIL | 跳通过率 | FK违规 | 状态
  ------|------|------|------|---------|--------|-----
  R1    | 8    | 6    | 2    | 75%     | 1      | ✅完成
  R2    | 8    | 7    | 1    | 87.5%   | 0      | ✅完成
  R3    | --   | --   | --   | --      | --     | ⏳待执行

准出状态: PENDING (需完成 Round 3)
```

---

## GATE 模式 (gate)

执行准出门禁检查，4 项条件全部通过才算 PASS：

```
if (round_count < 3) → FAIL: "强制 3 轮，当前仅 {N} 轮"
if (P0_fail > 0) → FAIL: "{N} 条 P0 断言失败"
if (hop_rate < 90%) → FAIL: "跳通过率 {rate}% < 90%"
if (fk_violations > 0) → FAIL: "{N} 处 FK 违规"
All pass → PASS → generate graduation-report.md
```

输出格式：

```
🚪 准出门禁检查 — {chain}

| 条件 | 状态 | 详情 |
|------|------|------|
| 3 轮完成 | ✅/❌ | Round {N}/3 |
| P0 全 PASS | ✅/❌ | {detail} |
| hop_rate >= 90% | ✅/❌ | 当前 {rate}% |
| FK 合规 | ✅/❌ | {N} 处违规 |
| **准出结论** | **PASS/FAIL** | |
```

---

## AUTO 模式 (auto)

```
if (no round files exist) → round 1
else if (latest round < 3) → round next
else if (round 3 exists) → gate
```

---

## 文件结构

```
{project}/docs/arch-analysis/
├── collected-data/
├── verification/
│   ├── round-1-verification.md    # Round 1 (immutable)
│   ├── round-2-verification.md    # Round 2 (immutable)
│   ├── round-3-verification.md    # Round 3 (immutable)
│   └── graduation-report.md      # Gate PASS 后生成
├── chains/
│   ├── {chain}-analysis.md        # 分析文档（可修正）
│   └── README.md
└── analysis-meta.json
```

---

## 重要规则

1. **每轮验证文档写入后禁止修改**: Round 文档是不可变记录
2. **Round 1 FAIL 项 -> 修正分析文档 -> Round 2 重新验证**: 验证文档与分析文档交替驱动
3. **FK-first**: 泛化主键（package_id / order_id / biz_no）自动标记为 FK 违规
4. **3 轮是强制要求，不是上限**: 必须完成 3 轮才能进入准出门禁
5. **每跳 SQL 必须包含 DB、索引、分片键注释**: 确保可复现
6. **准出门禁 4 条件全部通过才算 PASS**: 任一条件不满足即为 FAIL
