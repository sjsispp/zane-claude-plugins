---
name: arch-loop
description: "架构分析持续改进循环 — 识别薄弱环节并定向增强"
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
  - name: focus
    description: "depth — 增加分析深度（更多层级、更多链路）\ncoverage — 扩展覆盖范围（更多场景、更多表）\naccuracy — 提升准确性（修正验证失败项）\nfk — 专门修复 FK 违规\nauto — 自动识别最有价值的改进方向"
    required: false
    default: auto
---

# 架构分析持续改进循环

你是架构分析的持续改进引擎，负责在每轮迭代中识别并修复分析的薄弱环节。

## 参数解析

`$ARGUMENTS` = "{{$ARGUMENTS}}"

解析规则：
- `depth` → 深度优先改进
- `coverage` → 覆盖度优先改进
- `accuracy` → 准确性优先改进
- 无参数 / `auto` → 自动判断

---

## 执行流程

### Step 1: 读取当前状态

读取 `{project}/docs/arch-analysis/analysis-meta.json` 获取：

```json
{
  "project": "项目名",
  "version": "分析版本",
  "iteration": 1,
  "depth": "standard",
  "layers_completed": ["L0", "L1", "L2", "L3", "L4"],
  "verification": {
    "total": 60,
    "pass": 45,
    "fail": 3,
    "skip": 5,
    "pending": 7,
    "pass_rate": 0.75,
    "groups": {
      "G1": "pass",
      "G2": "pass",
      "G3": "partial",
      "G4": "pending",
      "G5": "pending"
    }
  },
  "scenarios_covered": ["场景A", "场景B"],
  "tables_verified": ["table1", "table2"],
  "last_updated": "2026-03-11T10:00:00Z"
}
```

### Step 2: 识别薄弱环节

#### 自动识别策略（auto 模式）

按优先级从高到低：

| 优先级 | 条件 | 改进方向 | 动作 |
|--------|------|---------|------|
| P0 | 验证轮次 < 3 | accuracy | 执行下一轮 /arch-verify round next |
| P1 | FK 违规 > 0 | fk | 修正分析文档 FK 关联 |
| P2 | Round 3 P0 FAIL > 0 | accuracy | 修正分析文档对应章节 |
| P3 | hop_pass_rate < 90% | accuracy | 分析 FAIL 原因并修正 |
| P4 | 未覆盖的核心场景 | coverage | 采集新场景数据 |
| P5 | 层级未完成 | depth | 推进下一层分析 |
| P6 | 准出门禁 PASS | -- | 建议停止循环 |

#### 指定模式策略

**depth 模式**：
1. 检查 `layers_completed`，推进未完成层级
2. 对已完成层级增加细节（如 L3 增加更多链路分析）
3. 增加 XRay trace 验证深度

**coverage 模式**：
1. 识别未覆盖的业务场景
2. 采集新场景的 DMS 数据
3. 增加表覆盖率

**accuracy 模式**：
1. 处理所有 FAIL 断言
2. 重新验证低置信度断言
3. 补充缺失的数据证据

**fk 模式**：
1. 读取最近一轮验证文档中的 FK 违规项
2. 对每个违规跳重新执行 FK 发现流程
3. 修正分析文档中的 FK 关联
4. 重新验证受影响的跳

### Step 3: 执行定向改进

根据 Step 2 识别结果，执行对应改进动作：

| 改进类型 | 执行方式 |
|---------|---------|
| REFACTOR | 调用 `/arch-verify refactor` |
| 继续验证 | 调用 `/arch-verify green {next_group}` |
| 新场景采集 | 启动子 Agent 采集 DMS + XRay |
| 层级推进 | 执行对应层级的分析 |
| 断言补充 | 设计新断言并执行 |

### Step 4: 重新验证受影响断言

改进完成后，重新验证受影响的断言组：
- 修正了 L0 分析 → 重新验证 G1
- 修正了 L5 分析 → 重新验证 G2
- 新增了场景 → 新增 G4/G5 断言并验证

### Step 5: 更新元数据

更新 `analysis-meta.json`：
- `iteration` + 1
- 更新 `verification` 统计
- 更新 `scenarios_covered` 和 `tables_verified`
- 记录 `last_updated`

---

## 输出格式

```
🔄 架构分析改进循环 — 第 {N} 轮

📊 当前状态:
  通过率: {pass_rate}% ({pass}/{total})
  层级: {layers} | 场景: {scenarios_count} | 表: {tables_count}

🎯 本轮改进方向: {focus}
  - {改进项1}: {原因}
  - {改进项2}: {原因}

📈 改进结果:
  通过率: {old}% → {new}%
  新增断言: +{N} | 修正: {M} | 新覆盖场景: {S}

⏭️ 下一步建议:
  1. /arch-loop {next_focus}
  2. /arch-verify status
```

---

## 退出条件

满足以下任一条件时，建议用户停止循环：

1. 准出门禁 PASS（3 轮完成 + P0 全 PASS + hop_rate >= 90% + FK 合规）
2. 迭代 >= 5 轮且指标无提升
3. 用户明确表示分析深度足够

退出时输出最终报告：
```
✅ 架构分析完成 — 第 {N} 轮后稳定

准出门禁: {PASS/FAIL}
验证轮次: {rounds}/3
最终跳通过率: {rate}%
FK 违规: {N}
层级覆盖: {layers}
场景覆盖: {scenarios}
表覆盖: {tables}

输出文件:
- docs/architecture-analysis.md (分析文档)
- docs/arch-analysis/verification/round-{1,2,3}-verification.md (验证文档)
- docs/arch-analysis/verification/graduation-report.md (准出报告)
- docs/arch-analysis/chains/{chain}-analysis.md (链路分析)
- docs/arch-analysis/analysis-meta.json (元数据)
```
